import sys
import pathlib
import logging
from datetime import *
import yaml

import troute.network.nhd_io as nhd_io
from .log_level_set import log_level_set
from troute.config import Config

LOG = logging.getLogger('')

def _input_handler_v04(args):
    '''
    Read user inputs from configuration file using troute.config module
    and set logging level

    Arguments
    ---------
    Args (argparse.Namespace): Command line input arguments

    Returns
    -------
    log_parameters               (dict): Input parameters re logging
    preprocessing_parameters     (dict): Input parameters re preprocessing
    supernetwork_parameters      (dict): Input parameters re network extent
    waterbody_parameters         (dict): Input parameters re waterbodies
    compute_parameters           (dict): Input parameters re computation settings
    forcing_parameters           (dict): Input parameters re model forcings
    restart_parameters           (dict): Input parameters re model restart
    hybrid_parameters            (dict): Input parameters re MC/diffusive wave model
    output_parameters            (dict): Input parameters re output writing
    parity_parameters            (dict): Input parameters re parity assessment
    data_assimilation_parameters (dict): Input parameters re data assimilation

    '''
    # get name of user configuration file (e.g. test.yaml)
    custom_input_file = args.custom_input_file

    with open(custom_input_file) as custom_file:
        data = yaml.load(custom_file, Loader=yaml.SafeLoader)

    troute_configuration = Config.with_strict_mode(**data)
    config_dict = troute_configuration.dict()

    log_parameters = config_dict.get('log_parameters')
    compute_parameters = config_dict.get('compute_parameters')
    network_topology_parameters = config_dict.get('network_topology_parameters')
    output_parameters = config_dict.get('output_parameters')
    bmi_parameters = config_dict.get('bmi_parameters')

    preprocessing_parameters = network_topology_parameters.get('preprocessing_parameters')
    supernetwork_parameters = network_topology_parameters.get('supernetwork_parameters')
    waterbody_parameters = network_topology_parameters.get('waterbody_parameters')
    forcing_parameters = compute_parameters.get('forcing_parameters')
    restart_parameters = compute_parameters.get('restart_parameters')
    hybrid_parameters = compute_parameters.get('hybrid_parameters')
    parity_parameters = output_parameters.get('wrf_hydro_parity_check')
    data_assimilation_parameters = compute_parameters.get('data_assimilation_parameters')

    # configure python logger
    log_level_set(log_parameters)

    return (
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
    )

def _input_handler_v03(args):

    '''
    Read user inputs from configuration file and set logging level

    Arguments
    ---------
    Args (argparse.Namespace): Command line input arguments

    Returns
    -------
    log_parameters               (dict): Input parameters re logging
    preprocessing_parameters     (dict): Input parameters re preprocessing
    supernetwork_parameters      (dict): Input parameters re network extent
    waterbody_parameters         (dict): Input parameters re waterbodies
    compute_parameters           (dict): Input parameters re computation settings
    forcing_parameters           (dict): Input parameters re model forcings
    restart_parameters           (dict): Input parameters re model restart
    hybrid_parameters            (dict): Input parameters re MC/diffusive wave model
    output_parameters            (dict): Input parameters re output writing
    parity_parameters            (dict): Input parameters re parity assessment
    data_assimilation_parameters (dict): Input parameters re data assimilation

    '''
    # get name of user configuration file (e.g. test.yaml)
    custom_input_file = args.custom_input_file

    # read data from user configuration file
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
    ) = nhd_io.read_config_file(custom_input_file)

    # configure python logger
    log_level_set(log_parameters)
    LOG = logging.getLogger('')

    # if log level is at or below DEBUG, then check user inputs
    if LOG.level <= 10: # DEBUG
        check_inputs(
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
                data_assimilation_parameters
                )

    return (
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
    )


def _does_file_exist(parameter_name, filepath_input):
    '''
    A test to see if input parameter files were provided by the user and that
    those files exist

    Arguments
    ---------
    - parameter_name (str): Name of the input parameter

    - filepath_input (str): Path of the input file to be checked

    Returns
    -------
    - No returns, just logging messages.
    '''

    LOG.debug(
        "Checking that a %s parameter is specified and the file exists",
        parameter_name
    )

    try:
        J = pathlib.Path(filepath_input)
        assert J.is_file() == True

    # file does not exist
    except AssertionError:

        LOG.error(
            'ERROR: %s parameter entry %s does not exist!!',
            parameter_name,
            filepath_input
        )
        LOG.error(
            'Make sure the file path is correctly entered in the configuration file'
        )
        sys.exit()

    # parameter is not provided by the user
    except KeyError:
        LOG.error(
            'A %s parameter is not provided in the configuration file',
            parameter_name
        )
        sys.exit()

    # test passed
    LOG.debug('The %s parameter is specified and exists', parameter_name)

def _does_path_exist(parameter_name, directory_path_input):
    '''
    A test to see if an input parameter directory is provided by the user and
    that the directory exist

    Arguments
    ---------
    - parameter_name       (str): Name of the input parameter

    - directory_path_input (str): Path of the input directory to be checked

    Returns
    -------
    - No returns, just logging messages.
    '''

    LOG.debug(
        'Checking that a %s parameter is specified and that the directory exists',
        parameter_name
    )

    try:
        J = pathlib.Path(directory_path_input)
        assert J.is_dir() == True

    except AssertionError:

        LOG.error(
            'ERROR: %s parameter entry %s does not exist!!',
            parameter_name,
            directory_path_input
        )
        LOG.error(
            'Make sure the directory path is correctly entered in the configuration file'
        )
        sys.exit()

    except KeyError:
        LOG.error(
            'A %s parameter must be specified in the configuration file'
            ,
            parameter_name
        )
        sys.exit()

    LOG.debug('The %s parameter is specified and exists', parameter_name)

def check_inputs(
            log_parameters,
            preprocessing_parameters,
            supernetwork_parameters,
            waterbody_parameters,
            compute_parameters,
            forcing_parameters,
            restart_parameters,
            diffusive_parameters,
            output_parameters,
            parity_parameters,
            data_assimilation_parameters
            ):

    LOG.debug('***** Begining configuration file (.YAML) check *****')

    #-----------------------------------------------------------------
    # If only preprocessing, make sure output directory exists
    #-----------------------------------------------------------------
    if preprocessing_parameters.get('preprocess_only', None):

        LOG.debug('Preparing a preprocessing only execution: preprocess_only = True')

        # if pre-processing the network graph data, check to make sure the destination
        # folder is specified
        if preprocessing_parameters.get('preprocess_output_folder',False):
            pass
        else:
            LOG.error(
                "No destination folder specified for preprocessing. Please specify preprocess_output_folder in the configuration file"
            )
            quit()

        # ... and check to make sure the destination folder exists
        _does_path_exist(
            'preprocess_output_folder',
            preprocessing_parameters['preprocess_output_folder']
        )

    #-----------------------------------------------------------------
    # User cannot set both preprocess_only and use_preprocessed_data
    # to true. It needs to be one or the other.
    #-----------------------------------------------------------------
    if preprocessing_parameters.get('preprocess_only', None) \
    and preprocessing_parameters.get('use_preprocessed_data', None):

        LOG.error("preprocess_only = True and use_preprocessed_data = True.")
        LOG.error('Aborting execution. Both variables cannot be True')
        quit()

    #-----------------------------------------------------------------
    # If preprocessed network data is to be used to to jump-start a
    # simulation, then check that the preprocessed file is provided
    # and that the file exists.
    #-----------------------------------------------------------------
    if preprocessing_parameters.get('use_preprocessed_data', None):

        LOG.debug(
            'Preparing a simlation that uses preprocessed network data: use_preprocessed_data = True'
        )

        # if user requests to use ready preprocessed data, check to make sure that the .npy file
        # containing network graph objects is specified.
        if preprocessing_parameters.get('preprocess_source_file',False):
            pass
        else:
            LOG.error(
                "No preprocessed .npy file specified."
            )
            LOG.error('Please specify preprocess_source_file in the configuration file')
            quit()

        # ... and check to make sure the source file exists
        _does_file_exist(
            'preprocess_source_file',
            preprocessing_parameters['preprocess_source_file']
        )

    #-----------------------------------------------------------------
    # Check that geo_file_path is provided and exists
    #-----------------------------------------------------------------
    _does_file_exist('geo_file_path',
                     supernetwork_parameters['geo_file_path'])

    #-----------------------------------------------------------------
    # Check if mask file is provided. If so, make sure the file exists
    # If no mask is provided, write a logging message warning the user
    # that no mask will be applied to the domain.
    #-----------------------------------------------------------------
    if supernetwork_parameters.get('mask_file_path', None):
        _does_file_exist('mask_file_path',
                     supernetwork_parameters['mask_file_path'])
    else:
        LOG.debug(
            'No user specified mask file. No mask will be applied to the channel domain.'
        )

    #-----------------------------------------------------------------
    # Checking waterbody parameter inputs....
    #
    # For a simulation with waterbodies,
    # break_network_at_waterbodies = True
    #-----------------------------------------------------------------
    if waterbody_parameters.get('break_network_at_waterbodies', None):

        #-------------------------------------------------------------
        # A levelpool waterbody parameter file must be provided for
        # any simulation with waterbodies. Check that a file was
        # specified and that the file exists.
        #-------------------------------------------------------------
        _does_file_exist('level_pool_waterbody_parameter_file_path',
                     waterbody_parameters['level_pool']
                         ['level_pool_waterbody_parameter_file_path'])

        #-------------------------------------------------------------
        # TODO: Include reservoir DA checks either here or elsewhere
        #-------------------------------------------------------------

    else:
        LOG.debug(
            'break_network_at_waterbodies == False or is not specified.')

        LOG.debug('No waterbodies will be simulated.')

    #-----------------------------------------------------------------
    # Checking restart inputs
    #-----------------------------------------------------------------
    if restart_parameters.get('wrf_hydro_channel_restart_file', None):

        _does_file_exist(
            'wrf_hydro_channel_restart_file',
            restart_parameters['wrf_hydro_channel_restart_file']
        )

        _does_file_exist(
            'wrf_hydro_waterbody_ID_crosswalk_file',
            restart_parameters['wrf_hydro_waterbody_ID_crosswalk_file']
        )

        _does_file_exist(
            'wrf_hydro_waterbody_crosswalk_filter_file',
            restart_parameters['wrf_hydro_waterbody_crosswalk_filter_file']
        )

    else:
        LOG.debug('No channel restart file specified, simulation will begin from a cold start')

    #-----------------------------------------------------------------
    # Checking forcing inputs
    #-----------------------------------------------------------------
    qlat_folder = forcing_parameters.get('qlat_input_folder',None)
    qlat_sets = forcing_parameters.get('qlat_forcing_sets', None)
    qlat_input_file = forcing_parameters.get('qlat_forcing_sets', None)

    if qlat_sets:

        if qlat_sets[0].get('qlat_files', None):

            _does_path_exist(
                'qlat_input_folder',
                forcing_parameters['qlat_input_folder']
            )

            qlat_input_folder = pathlib.Path(forcing_parameters['qlat_input_folder'])
            for (s, _) in enumerate(qlat_sets):

                for i, f in enumerate(qlat_sets[s]['qlat_files']):

                    _does_file_exist(
                        'qlat_files[{}][{}]'.format(s, i),
                        qlat_input_folder.joinpath(f)
                    )

        elif qlat_sets[0].get('qlat_input_file', None):

            for (s, _) in enumerate(qlat_sets):

                _does_file_exist(
                    'qlat_input_file',
                    qlat_sets[s]['qlat_input_file']
                )

        else:
            errmsg = 'if qlat_forcing_sets variable is in the configuration file, \
            explicitly listed forcing files are expected for each simulation loop. \
            Expected to find qlat_files or qlat_input_file variables in each of the \
            qlat_forcing_sets variable groups.'
            LOG.error(errmsg)

    else:

        _does_path_exist(
            'qlat_input_folder',
            forcing_parameters['qlat_input_folder']
        )
    #-----------------------------------------------------------------
    # Checking streamflow data assimilation inputs
    #-----------------------------------------------------------------
    streamflow_da = data_assimilation_parameters.get('streamflow_da', None)
    if streamflow_da:
        if streamflow_da.get('streamflow_nudging', False):
            LOG.debug(
                'streamflow_nudging == True, so simulation will include streamflow DA'
            )

            # make sure a USGS TimeSlices directory is provided
            _does_path_exist(
                'usgs_timeslices_folder',
                data_assimilation_parameters['usgs_timeslices_folder']
            )

            # make sure a gage<>segment ID crosswalk file is provided
            _does_file_exist(
                'gage_segID_crosswalk_file',
                streamflow_da['gage_segID_crosswalk_file']
            )
            #-----------------------------------------------------------------
            # Checking for lastobs file
            #-----------------------------------------------------------------
            if streamflow_da.get('wrf_hydro_lastobs_file', None):

                _does_file_exist(
                    'wrf_hydro_lastobs_file',
                    streamflow_da['wrf_hydro_lastobs_file']
                )

            else:
                LOG.debug('No Lastobs file provided for streamflow DA.')

            #-----------------------------------------------------------------
            # Checking for lastobs output folder
            #-----------------------------------------------------------------
            if data_assimilation_parameters.get('lastobs_output_folder', None):

                _does_path_exist(
                    'lastobs_output_folder',
                    data_assimilation_parameters['lastobs_output_folder']
                )
            else:
                LOG.debug(
                    'No LastObs output folder specified. LastObs data will not be written out.'
                )

        else:
            LOG.debug('streamflow_nudging specified as or assumed to be False.')
            LOG.debug('Simulation will NOT include streamflow DA')

    else:
        LOG.debug('No streamflow_da parameters provided.')
        LOG.debug('Simulation will NOT include streamflow DA')

    #-----------------------------------------------------------------
    # Checking reservoir data assimilation inputs
    #-----------------------------------------------------------------
    reservoir_da = data_assimilation_parameters.get('reservoir_da', None)
    if reservoir_da:
        reservoir_persistence_usgs  = reservoir_da.get('reservoir_persistence_usgs', False)
        reservoir_persistence_usace = reservoir_da.get('reservoir_persistence_usace', False)
        #-----------------------------------------------------------------
        # USGS Hybrid inputs
        #-----------------------------------------------------------------
        if reservoir_persistence_usgs:
            LOG.debug(
                'reservoir_persistence_usgs == True, so simulation will include USGS persistence reservoir DA'
            )
            _does_path_exist(
                'usgs_timeslices_folder',
                data_assimilation_parameters['usgs_timeslices_folder']
            )
        #-----------------------------------------------------------------
        # USACE Hybrid inputs
        #-----------------------------------------------------------------
        if reservoir_persistence_usace:
            LOG.debug(
                'reservoir_persistence_usace == True, so simulation will include USACE persistence reservoir DA'
            )
            _does_path_exist(
                'usace_timeslices_folder',
                data_assimilation_parameters['usace_timeslices_folder']
            )
        #-----------------------------------------------------------------
        # Make sure crosswalk file exists, for either USGS or USACE hydbrid
        #-----------------------------------------------------------------
        if reservoir_persistence_usgs or reservoir_persistence_usace:

            _does_file_exist(
                'gage_lakeID_crosswalk_file',
                reservoir_da['gage_lakeID_crosswalk_file']
            )
    #-----------------------------------------------------------------
    # Checking output settings
    #-----------------------------------------------------------------
    if output_parameters.get('csv_output', None):

        if output_parameters['csv_output'].get('csv_output_folder', None):

            _does_path_exist(
                'csv_output_folder',
                output_parameters['csv_output']['csv_output_folder']
            )

            output_segs = output_parameters['csv_output'].get('csv_output_segments', None)
            if not output_segs:
                LOG.debug('No csv output segments specified. Results for all domain segments will be written')

        else:
            LOG.debug('No csv output folder specified. Results will NOT be written to csv')

    else:
        LOG.debug('No csv output folder specified. Results will NOT be written to csv')

    if output_parameters.get('parquet_output', None):

        if output_parameters['parquet_output'].get('parquet_output_folder', None):

            _does_path_exist(
                'parquet_output_folder',
                output_parameters['parquet_output']['parquet_output_folder']
            )

            output_segs = output_parameters['parquet_output'].get('parquet_output_segments', None)
            if not output_segs:
                LOG.debug('No parquet output segments specified. Results for all domain segments will be written')

        else:
            LOG.debug('No parquet output folder specified. Results will NOT be written in parquet format')

    else:
        LOG.debug('No parquet output folder specified. Results will NOT be written in parquet format')

    if output_parameters.get('chrtout_output', None):

        if output_parameters['chrtout_output'].get('chrtout_read_folder', None):

            _does_path_exist(
                'chrtout_read_folder',
                output_parameters['chrtout_output']['chrtout_read_folder']
            )

            if output_parameters['chrtout_output'].get('chrtout_write_folder', None):

                _does_path_exist(
                    'chrtout_write_folder',
                    output_parameters['chrtout_output']['chrtout_write_folder']
                )

            else:
                LOG.debug('No chrtout_output folder specified. Defaulting CHRTOUT write location to chrtout_read_folder')

        else:
            LOG.debug('No chrtout_output parameter specified. Results will NOT be written to CHRTOUT')
    else:
        LOG.debug('No chrtout_output parameter specified. Results will NOT be written to CHRTOUT')

    if output_parameters.get('hydro_rst_output', None):

        if output_parameters['hydro_rst_output'].get('wrf_hydro_channel_restart_source_directory', None):

            _does_path_exist(
                'wrf_hydro_channel_restart_source_directory',
                output_parameters['hydro_rst_output']['wrf_hydro_channel_restart_source_directory']
            )

            if output_parameters['hydro_rst_output'].get('wrf_hydro_channel_restart_output_directory', None):

                _does_path_exist(
                    'wrf_hydro_channel_restart_output_directory',
                    output_parameters['hydro_rst_output']['wrf_hydro_channel_restart_output_directory']
                )

            else:
                LOG.debug('No wrf_hydro_channel_restart_output_directory folder specified. Defaulting write location to wrf_hydro_channel_restart_source_directory')

        else:
            LOG.debug('No hydro_rst_output parameter specified. Restart data will NOT be written out')

    else:
        LOG.debug('No hydro_rst_output parameter specified. Restart data will NOT be written out')


    # TODO Parity Check files

    # TODO summarize simlation configuration


    LOG.debug('***** Configuration file check complete *****')
