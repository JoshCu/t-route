import argparse
import time
import logging
from datetime import timedelta

from troute.network.NHDNetwork import NHDNetwork
from troute.network.HYFeaturesNetwork import HYFeaturesNetwork
from troute.network.DataAssimilation import DataAssimilation

import pandas as pd

from .input import  _input_handler_v04
from .output import nwm_output_generator
from troute.routing.compute import compute_nhd_routing_v02, compute_diffusive_routing, compute_log_mc, compute_log_diff

import troute.network.nhd_io as nhd_io
import troute.network.nhd_network_utilities_v02 as nnu
import troute.network.hyfeature_network_utilities as hnu


LOG = logging.getLogger()
LOG.setLevel(logging.INFO)
# set default console handler
LOG.addHandler(logging.StreamHandler())

'''
High level orchestration of ngen t-route simulations for NWM application
'''
def main_v04(argv):

    args = _handle_args_v03(argv)

    # unpack user inputs
    (
        log_parameters,
        preprocessing_parameters,
        supernetwork_parameters,
        waterbody_parameters,
        compute_parameters,
        forcing_parameters,
        restart_parameters,
        hybrid_parameters,
        output_parameters,
        parity_parameters,
        data_assimilation_parameters,
    ) = _input_handler_v04(args)

    run_parameters = {
        'dt': forcing_parameters.get('dt'),
        'nts': forcing_parameters.get('nts'),
        'cpu_pool': compute_parameters.get('cpu_pool'),
    }

    showtiming = log_parameters.get("showtiming", None)


    task_times = {}
    task_times['forcing_time'] = 0
    task_times['route_time'] = 0
    task_times['output_time'] = 0
    main_start_time = time.time()

    cpu_pool = compute_parameters.get("cpu_pool", None)

    # Build routing network data objects. Network data objects specify river
    # network connectivity, channel geometry, and waterbody parameters. Also
    # perform initial warmstate preprocess.

    network_start_time = time.time()

    #if "ngen_nexus_file" in supernetwork_parameters:
    if supernetwork_parameters["network_type"] == 'HYFeaturesNetwork':
        network = HYFeaturesNetwork(supernetwork_parameters,
                                    waterbody_parameters,
                                    data_assimilation_parameters,
                                    restart_parameters,
                                    compute_parameters,
                                    forcing_parameters,
                                    hybrid_parameters,
                                    preprocessing_parameters,
                                    output_parameters,
                                    verbose=True, showtiming=showtiming)
        duplicate_ids_df = network._duplicate_ids_df

    elif supernetwork_parameters["network_type"] == 'NHDNetwork':
        network = NHDNetwork(supernetwork_parameters,
                             waterbody_parameters,
                             restart_parameters,
                             forcing_parameters,
                             compute_parameters,
                             data_assimilation_parameters,
                             hybrid_parameters,
                             output_parameters,
                             verbose=True,
                             showtiming=showtiming,
                            )
        duplicate_ids_df = pd.DataFrame()


    network_end_time = time.time()
    task_times['network_creation_time'] = network_end_time - network_start_time

    # Create run_sets: sets of forcing files for each loop
    run_sets = network.build_forcing_sets()

    # Create da_sets: sets of TimeSlice files for each loop
    if "data_assimilation_parameters" in compute_parameters:
        da_sets = hnu.build_da_sets(data_assimilation_parameters, run_sets, network.t0)

    # Create parity_sets: sets of CHRTOUT files against which to compare t-route flows
    if output_parameters.get("wrf_hydro_parity_check"):
        parity_sets = nnu.build_parity_sets(parity_parameters, run_sets)
    else:
        parity_sets = []

    # Create forcing data within network object for first loop iteration
    network.assemble_forcings(run_sets[0],)

    # Create data assimilation object from da_sets for first loop iteration
    data_assimilation = DataAssimilation(
        network,
        data_assimilation_parameters,
        run_parameters,
        waterbody_parameters,
        from_files=True,
        value_dict=None,
        da_run=da_sets[0],
        )


    forcing_end_time = time.time()
    task_times['forcing_time'] += forcing_end_time - network_end_time

    parallel_compute_method = compute_parameters.get("parallel_compute_method", None)
    subnetwork_target_size = compute_parameters.get("subnetwork_target_size", 1)
    qts_subdivisions = forcing_parameters.get("qts_subdivisions", 1)
    compute_kernel = compute_parameters.get("compute_kernel", "V02-caching")
    assume_short_ts = compute_parameters.get("assume_short_ts", False)
    return_courant = compute_parameters.get("return_courant", False)

    logFileName = 'NONE'
    kernelTalks = log_parameters.get("log_directory", None)
    if kernelTalks:
        logFileName = kernelTalks+'/kernelTalks.log'
        with open(logFileName, 'w') as preRunLog:
            preRunLog.write("************************************************************\n")
            preRunLog.write("Pre- and post run parameter and run statistics output file. \n")
            preRunLog.write("************************************************************\n")
            preRunLog.write("\n")
            preRunLog.write("-----\n")

            if (restart_parameters['lite_channel_restart_file']==None):
                outPutStr = "No channel restart file: cold start."
                preRunLog.write(outPutStr+"\n")
                LOG.info(outPutStr)
            else:
                outPutStr = "Warmstart - restart file: "+restart_parameters['lite_channel_restart_file']
                preRunLog.write(outPutStr+" \n")
                LOG.info(outPutStr)

            if (restart_parameters['lite_waterbody_restart_file']==None):
                outPutStr = "No waterbody restart file."
                preRunLog.write(outPutStr+"\n")
                LOG.info(outPutStr)
            else:
                outPutStr = "Waterbody restart file: "+restart_parameters['lite_waterbody_restart_file']
                preRunLog.write(outPutStr+" \n")
                LOG.info(outPutStr)

            preRunLog.write("-----\n")
            preRunLog.write("\n")
            preRunLog.close()

    # Pass empty subnetwork list to nwm_route. These objects will be calculated/populated
    # on first iteration of for loop only. For additional loops this will be passed
    # to function from inital loop.
    subnetwork_list = [None, None, None]

    # Flag for first run for param output
    firstRun = True
    # Disable in case there is no log file
    if (not kernelTalks):
        firstRun = False

    for run_set_iterator, run in enumerate(run_sets):

        t0 = run.get("t0")
        dt = run.get("dt")
        nts = run.get("nts")

        if parity_sets:
            parity_sets[run_set_iterator]["dt"] = dt
            parity_sets[run_set_iterator]["nts"] = nts


        route_start_time = time.time()

        run_results = nwm_route(
            network.connections,
            network.reverse_network,
            network.waterbody_connections,
            network.reaches_by_tailwater,
            parallel_compute_method,
            compute_kernel,
            subnetwork_target_size,
            cpu_pool,
            network.t0,
            dt,
            nts,
            qts_subdivisions,
            network.independent_networks,
            network.dataframe,
            network.q0,
            network._qlateral,
            data_assimilation.usgs_df,
            data_assimilation.lastobs_df,
            data_assimilation.reservoir_usgs_df,
            data_assimilation.reservoir_usgs_param_df,
            data_assimilation.reservoir_usace_df,
            data_assimilation.reservoir_usace_param_df,
            data_assimilation.reservoir_rfc_df,
            data_assimilation.reservoir_rfc_param_df,
            data_assimilation.great_lakes_df,
            data_assimilation.great_lakes_param_df,
            network.great_lakes_climatology_df,
            data_assimilation.assimilation_parameters,
            assume_short_ts,
            return_courant,
            network.waterbody_dataframe,
            data_assimilation_parameters,
            network.waterbody_types_dataframe,
            network.waterbody_type_specified,
            network.diffusive_network_data,
            network.topobathy_df,
            network.refactored_diffusive_domain,
            network.refactored_reaches,
            subnetwork_list,
            network.coastal_boundary_depth_df,
            network.unrefactored_topobathy_df,
            firstRun,
            logFileName
        )

        # returns list, first item is run result, second item is subnetwork items
        subnetwork_list = run_results[1]
        run_results = run_results[0]


        route_end_time = time.time()
        task_times['route_time'] += route_end_time - route_start_time

        # create initial conditions for next loop itteration
        network.new_q0(run_results)
        network.update_waterbody_water_elevation()

        # update reservoir parameters and lastobs_df
        data_assimilation.update_after_compute(run_results, dt*nts)

        # TODO move the conditional call to write_lite_restart to nwm_output_generator.
        if output_parameters:
            if output_parameters['lite_restart'] is not None:
                nhd_io.write_lite_restart(
                    network.q0,
                    network._waterbody_df,
                    t0 + timedelta(seconds = dt * nts),
                    output_parameters['lite_restart']
                )

        # Prepare input forcing for next time loop simulation when mutiple time loops are presented.
        if run_set_iterator < len(run_sets) - 1:
            # update t0
            network.new_t0(dt,nts)

            # update forcing data
            network.assemble_forcings(run_sets[run_set_iterator + 1],)

            # get reservoir DA initial parameters for next loop iteration
            data_assimilation.update_for_next_loop(
                network,
                da_sets[run_set_iterator + 1])


            forcing_end_time = time.time()
            task_times['forcing_time'] += forcing_end_time - route_end_time

        if network.poi_nex_dict:
            poi_crosswalk = network.poi_nex_dict
        else:
            poi_crosswalk = dict()

        output_start_time = time.time()

        #TODO Update this to work with either network type...
        nwm_output_generator(
            run,
            run_results,
            supernetwork_parameters,
            output_parameters,
            parity_parameters,
            restart_parameters,
            parity_sets[run_set_iterator] if parity_parameters else {},
            qts_subdivisions,
            compute_parameters.get("return_courant", False),
            cpu_pool,
            network.waterbody_dataframe,
            network.waterbody_types_dataframe,
            duplicate_ids_df,
            data_assimilation_parameters,
            data_assimilation.lastobs_df,
            network.link_gage_df,
            network.link_lake_crosswalk,
            network.nexus_dict,
            poi_crosswalk,
            logFileName
        )


        output_end_time = time.time()
        task_times['output_time'] += output_end_time - output_start_time

        firstRun = False

    # end of for run_set_iterator, run in enumerate(run_sets):


    task_times['total_time'] = time.time() - main_start_time

    LOG.debug("process complete in %s seconds." % (time.time() - main_start_time))

    LOG.info('************ TIMING SUMMARY ************')
    LOG.info('----------------------------------------')
    LOG.info(
        'Network graph construction: {} secs, {} %'\
        .format(
            round(task_times['network_creation_time'], 2),
            round(task_times['network_creation_time'] / task_times['total_time'] * 100, 2)
        )
    )
    LOG.info(
        'Forcing array construction: {} secs, {} %'\
        .format(
            round(task_times['forcing_time'], 2),
            round(task_times['forcing_time'] / task_times['total_time'] * 100, 2)
        )
    )
    LOG.info(
        'Routing computations: {} secs, {} %'\
        .format(
            round(task_times['route_time'], 2),
            round(task_times['route_time'] / task_times['total_time'] * 100, 2)
        )
    )
    LOG.info(
        'Output writing: {} secs, {} %'\
        .format(
            round(task_times['output_time'], 2),
            round(task_times['output_time'] / task_times['total_time'] * 100, 2)
        )
    )
    LOG.info('----------------------------------------')
    LOG.info(
        'Total execution time: {} secs'\
        .format(
            round(task_times['network_creation_time'], 2) +
            round(task_times['forcing_time'], 2) +
            round(task_times['route_time'], 2) +
            round(task_times['output_time'], 2)
        )
    )

    if showtiming and log_parameters.get('log_level') not in ['DEBUG', 'INFO']:
        print('************ TIMING SUMMARY ************')
        print('----------------------------------------')
        print(
            'Network graph construction: {} secs, {} %'\
            .format(
                round(task_times['network_creation_time'],2),
                round(task_times['network_creation_time']/task_times['total_time'] * 100,2)
            )
        )
        print(
            'Forcing array construction: {} secs, {} %'\
            .format(
                round(task_times['forcing_time'],2),
                round(task_times['forcing_time']/task_times['total_time'] * 100,2)
            )
        )
        print(
            'Routing computations: {} secs, {} %'\
            .format(
                round(task_times['route_time'],2),
                round(task_times['route_time']/task_times['total_time'] * 100,2)
            )
        )
        print(
            'Output writing: {} secs, {} %'\
            .format(
                round(task_times['output_time'],2),
                round(task_times['output_time']/task_times['total_time'] * 100,2)
            )
        )
        print('----------------------------------------')
        print(
            'Total execution time: {} secs'\
            .format(
                round(task_times['network_creation_time'],2) +
                round(task_times['forcing_time'],2) +
                round(task_times['route_time'],2) +
                round(task_times['output_time'],2)
            )
        )

def _handle_args_v03(argv):
    '''
    Handle command line input argument - filepath of configuration file
    '''
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-f",
        "--custom-input-file",
        dest="custom_input_file",
        help="Path of a .yaml or .json file containing model configuration parameters. See doc/v3_doc.yaml",
    )
    return parser.parse_args(argv)

def nwm_route(
    downstream_connections,
    upstream_connections,
    waterbodies_in_connections,
    reaches_bytw,
    parallel_compute_method,
    compute_kernel,
    subnetwork_target_size,
    cpu_pool,
    t0,
    dt,
    nts,
    qts_subdivisions,
    independent_networks,
    param_df,
    q0,
    qlats,
    usgs_df,
    lastobs_df,
    reservoir_usgs_df,
    reservoir_usgs_param_df,
    reservoir_usace_df,
    reservoir_usace_param_df,
    reservoir_rfc_df,
    reservoir_rfc_param_df,
    great_lakes_df,
    great_lakes_param_df,
    great_lakes_climatology_df,
    da_parameter_dict,
    assume_short_ts,
    return_courant,
    waterbodies_df,
    data_assimilation_parameters,
    waterbody_types_df,
    waterbody_type_specified,
    diffusive_network_data,
    topobathy_df,
    refactored_diffusive_domain,
    refactored_reaches,
    subnetwork_list,
    coastal_boundary_depth_df,
    unrefactored_topobathy_df,
    firstRun=False,
    logFileName='troute_run_log.txt',
    flowveldepth_interorder={},
    from_files=False,
):

    ################### Main Execution Loop across ordered networks
    start_time = time.time()

    if return_courant:
        LOG.info(
            "executing routing computation, with Courant evaluation metrics returned"
        )
    else:
        LOG.info("executing routing computation ...")

    if (firstRun):
        compute_log_mc(
            logFileName,
            downstream_connections,
            upstream_connections,
            waterbodies_in_connections,
            reaches_bytw,
            compute_kernel,
            parallel_compute_method,
            subnetwork_target_size,
            cpu_pool,
            t0,
            dt,
            nts,
            qts_subdivisions,
            independent_networks,
            param_df,
            q0,
            qlats,
            usgs_df,
            lastobs_df,
            reservoir_usgs_df,
            reservoir_usgs_param_df,
            reservoir_usace_df,
            reservoir_usace_param_df,
            reservoir_rfc_df,
            reservoir_rfc_param_df,
            assume_short_ts,
            waterbodies_df,
            data_assimilation_parameters,
            waterbody_types_df,
            waterbody_type_specified,
        )

    start_time_mc = time.time()
    results = compute_nhd_routing_v02(
        downstream_connections,
        upstream_connections,
        waterbodies_in_connections,
        reaches_bytw,
        compute_kernel,
        parallel_compute_method,
        subnetwork_target_size,  # The default here might be the whole network or some percentage...
        cpu_pool,
        t0,
        dt,
        nts,
        qts_subdivisions,
        independent_networks,
        param_df,
        q0,
        qlats,
        usgs_df,
        lastobs_df,
        reservoir_usgs_df,
        reservoir_usgs_param_df,
        reservoir_usace_df,
        reservoir_usace_param_df,
        reservoir_rfc_df,
        reservoir_rfc_param_df,
        great_lakes_df,
        great_lakes_param_df,
        great_lakes_climatology_df,
        da_parameter_dict,
        assume_short_ts,
        return_courant,
        waterbodies_df,
        data_assimilation_parameters,
        waterbody_types_df,
        waterbody_type_specified,
        subnetwork_list,
        flowveldepth_interorder,
        from_files = from_files,
    )
    LOG.debug("MC computation complete in %s seconds." % (time.time() - start_time_mc))
    # returns list, first item is run result, second item is subnetwork items
    subnetwork_list = results[1]
    results = results[0]

    # run diffusive side of a hybrid simulation
    if diffusive_network_data:
        start_time_diff = time.time()
        '''
        # retrieve MC-computed streamflow value at upstream boundary of diffusive mainstem
        qvd_columns = pd.MultiIndex.from_product(
            [range(nts), ["q", "v", "d"]]
        ).to_flat_index()
        flowveldepth = pd.concat(
            [pd.DataFrame(r[1], index=r[0], columns=qvd_columns) for r in results],
            copy=False,
        )
        '''
        #upstream_boundary_flow={}
        #for tw,v in  diffusive_network_data.items():
        #    upstream_boundary_link     = diffusive_network_data[tw]['upstream_boundary_link']
        #    flow_              = flowveldepth.loc[upstream_boundary_link][0::3]
            # the very first value at time (0,q) is flow value at the first time step after initial time.
        #    upstream_boundary_flow[tw] = flow_

        if (firstRun):
            compute_log_diff(
                logFileName,
                diffusive_network_data,
                topobathy_df,
                refactored_diffusive_domain,
                refactored_reaches,
                coastal_boundary_depth_df,
                unrefactored_topobathy_df,
            )

        # call diffusive wave simulation and append results to MC results
        results.extend(
            compute_diffusive_routing(
                results,
                diffusive_network_data,
                cpu_pool,
                t0,
                dt,
                nts,
                q0,
                qlats,
                qts_subdivisions,
                usgs_df,
                lastobs_df,
                da_parameter_dict,
                waterbodies_df,
                topobathy_df,
                refactored_diffusive_domain,
                refactored_reaches,
                coastal_boundary_depth_df,
                unrefactored_topobathy_df,
            )
        )
        LOG.debug("Diffusive computation complete in %s seconds." % (time.time() - start_time_diff))

    else:

        if (firstRun):
            with open(logFileName, 'a') as preRunLog:
                preRunLog.write("**********************\n")
                preRunLog.write("No diffusive routing. \n")
                preRunLog.write("**********************\n")
            preRunLog.close()

    LOG.debug("ordered reach computation complete in %s seconds." % (time.time() - start_time))

    return results, subnetwork_list

def main():
    v_parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    v_parser.add_argument(
        "-V",
        "--input-version",
        default=4,
        nargs="?",
        choices=[2, 3, 4],
        type=int,
        help="Use version 3 or 4 of the input format. Default 4",
    )
    v_args = v_parser.parse_known_args()


    LOG.info("Running main v04 - looping")
    main_v04(v_args[1])

if __name__ == "__main__":
    main()
