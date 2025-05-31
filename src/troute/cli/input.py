import logging
from datetime import *
import yaml

from .log_level_set import log_level_set
from troute.config import Config

LOG = logging.getLogger("")


def _input_handler_v04(args):
    """
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

    """
    # get name of user configuration file (e.g. test.yaml)
    custom_input_file = args.custom_input_file

    with open(custom_input_file) as custom_file:
        data = yaml.load(custom_file, Loader=yaml.SafeLoader)

    troute_configuration = Config.with_strict_mode(**data)
    config_dict = troute_configuration.dict()

    log_parameters = config_dict.get("log_parameters")
    compute_parameters = config_dict.get("compute_parameters")
    network_topology_parameters = config_dict.get("network_topology_parameters")
    output_parameters = config_dict.get("output_parameters")
    bmi_parameters = config_dict.get("bmi_parameters")

    preprocessing_parameters = network_topology_parameters.get("preprocessing_parameters")
    supernetwork_parameters = network_topology_parameters.get("supernetwork_parameters")
    waterbody_parameters = network_topology_parameters.get("waterbody_parameters")
    forcing_parameters = compute_parameters.get("forcing_parameters")
    restart_parameters = compute_parameters.get("restart_parameters")
    hybrid_parameters = compute_parameters.get("hybrid_parameters")
    parity_parameters = output_parameters.get("wrf_hydro_parity_check")
    data_assimilation_parameters = compute_parameters.get("data_assimilation_parameters")

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
