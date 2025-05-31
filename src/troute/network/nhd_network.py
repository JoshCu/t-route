from collections import defaultdict, deque
from itertools import chain
from functools import reduce
from toolz import pluck
from deprecated import deprecated
#Consider using sphinx for inlining deprecation into docstrings
#from deprecated.sphinx import deprecated

def reverse_dict(d):
    """
    Reverse a 1-1 mapping
    Values must be hashable!

    Arguments:
    ----------
    d (dict): Dictionary to be reversed

    Returns
    -------
    (dict): reversed dictionary

    """
    return {v: k for k, v in d.items()}

def extract_connections(rows, target_col, terminal_codes=None):
    '''
    Extract connection network from dataframe.

    Arguments:
    ----------
    rows (DataFrame): Dataframe indexed by key_col.
    key_col    (str): Source of each edge
    target_col (str): Target of edge

    Returns:
    --------
    network (dict, int: [int]): {segment id: [list of downstream adjacent segment ids]}

    '''
    if terminal_codes is not None:
        terminal_codes = set(terminal_codes)
    else:
        terminal_codes = {0}

    network = {}
    for src, dst in rows[target_col].items():
        if src not in network:
            network[src] = []

        if dst not in terminal_codes:
            network[src].append(dst)
    return network

@deprecated(version='2.4.0', reason="Functionality moved to Network classes")
def extract_waterbody_connections(rows, target_col = 'waterbody', waterbody_null=-9999):
    '''
    Extract waterbody mapping from parameter dataframe. Mapping segment ids to the lake ids they reside in

    Arguments
    ---------
    rows     (DataFrame): Waterbody id codes, indexed by segment id
    target_col     (str): Column name containing waterbody id codes in rows df (defalt: 'waterbody')
    waterbody_null (int): waterbody null code (default: -9999)

    Returns
    -------
    wbody_map (dict, int: int): {segment id: lake id}

    '''

    wbody_map = (rows.loc[rows[target_col] != waterbody_null, target_col].
                     astype("int").
                     to_dict()
                    )

    return wbody_map


def gage_mapping(segment_gage_df, gage_col="gages"):
    """
    Extract gage mapping from parameter dataframe. Mapping segment ids to gage ids

    Arguments
    ---------
    segment_gage_df (DataFrame): Gage id codes, indexed by segment id
    gage_col              (str): Column name containing gage id codes in segment_gage_df (default: 'gages')

    Returns
    -------
    gage_map (dict, int: byte string) {segment id: gage id}

    """

    gage_list = list(map(bytes.strip, segment_gage_df[gage_col].values))
    gage_mask = list(map(bytes.isalnum, gage_list))
    segment_gage_df = segment_gage_df.loc[gage_mask, [gage_col]]
    segment_gage_df[gage_col] = segment_gage_df[gage_col].apply(lambda x: x.decode('utf-8')).str.strip()
    gage_map = segment_gage_df.to_dict()
    return gage_map


def reverse_surjective_mapping(d):
    rd = defaultdict(list)
    for src, dst in d.items():
        rd[dst].append(src)
    rd.default_factory = None
    return rd


def reverse_network(N):
    '''
    Reverse network connections graph

    Arguments:
    ----------
    N (dict, int: [int]): downstream network connections

    Returns:
    --------
    rg (dict, int: [int]): upstream network connections

    '''
    rg = defaultdict(list)
    for src, dst in N.items():
        rg[src]
        for n in dst:
            rg[n].append(src)
    rg.default_factory = None
    return rg


def headwaters(N):
    '''
    Find network headwater segments

    Arguments
    ---------
    N (dict, int: [int]): Network connections graph

    Returns
    -------
    (iterable): headwater segments

    Notes
    -----
    - If reverse connections graph is handed as input, then function
      will return network tailwaters.

    '''
    return N.keys() - chain.from_iterable(N.values())

def tailwaters(N):
    '''
    Find network tailwaters

    Arguments
    ---------
    N (dict, int: [int]): Network connections graph

    Returns
    -------
    (iterable): tailwater segments

    Notes
    -----
    - If reverse connections graph is handed as input, then function
      will return network headwaters.

    '''
    tw = chain.from_iterable(N.values()) - N.keys()
    for m, n in N.items():
        if not n:
            tw.add(m)
    return tw

def reachable(N, sources=None, targets=None):
    """
    Return segments reachable from sources.

    Arguments:
    ----------
    N (dict, int: [int]): Reverse network connections
    sources (iterable): Segments from which to start searches.
                        If none, network tailwaters are used
    targets (iterable): Target segments to stop searching.

    Returns:
    rv (dict, int: set(int)): Segments reachble from sources. Sources are dictionary keys,
                              reachable segments are dictionary values.

    """
    if sources is None:
        sources = headwaters(N)

    rv = {}
    if targets is None:
        for h in sources:
            reach = set()
            Q = deque([h])
            while Q:
                x = Q.popleft()
                reach.add(x)
                Q.extend(N.get(x, ()))
            rv[h] = reach
    else:
        targets = set(targets)

        for h in sources:
            reach = set()
            Q = deque([h])
            while Q:
                x = Q.popleft()
                reach.add(x)
                if x not in targets:
                    Q.extend(N.get(x, ()))
            rv[h] = reach
    return rv


def reachable_network(N, sources=None, targets=None, check_disjoint=True):
    """
    Return subnetworks generated by reach
    Arguments:
    ----------
    N (dict, int: [int]): Reverse network connections dictionary
    sources (iterable): Segments to begin search from. If None, source nodes are used.
    targets (iterable): Target nodes to stop searching
    check_disjoint (bool):

    Returns:
    --------
    rv (dict, {int, {int: [int]}}): Reverse connections dictionary for each independent network
                                    highest level key is the network tailwater id.

    """
    # identify all segments reachable from each terminal segment (e.g. tailwater)
    reached = reachable(N, sources=sources, targets=targets)

    # check network connectivity
    if (
        check_disjoint
        and len(reached) > 1
        and reduce(set.intersection, reached.values())
    ):
        raise ValueError("Networks not disjoint")

    rv = {}
    for k, n in reached.items():
        rv[k] = {m: N.get(m, []) for m in n}
    return rv


def split_at_junction(network, path, node):
    '''
    Identify reach break points at junctions.

    Arguments:
    ----------
    network (dict): Reverse connections graph
    path    (list): List of segments along search path
    node     (int): Stream segment under inquiry

    Returns:
    --------
    (bool): False if segment is a network break point, True otherwise

    '''
    return len(network[node]) == 1

def split_at_gages_waterbodies_and_junctions(gage_nodes, waterbody_nodes, network, path, node):
    '''
    Identify reach break points at stream gages, waterbodies and junctions.

    Arguments:
    ----------
    gage_nodes      (set): Nodes with gages
    waterbody_nodes (set): Nodes within waterbodies
    network        (dict): Reverse connections graph
    path           (list): List of segments along search path
    node            (int): Stream segment under inquiry

    Returns:
    --------
    (bool): False if segment is a network break point, True otherwise

    '''
    if (path[-1] in gage_nodes) | (node in gage_nodes):
        return False  # force a path split if coming from or going to a gage node
    if (path[-1] in waterbody_nodes) ^ (node in waterbody_nodes):
        return False  # force a path split if entering or exiting a waterbody
    else:
        return len(network[node]) == 1

def split_at_gages_and_junctions(gage_nodes, network, path, node):
    '''
    Identify reach break points at stream gages and junctions.

    Arguments:
    ----------
    gage_nodes (set): Nodes with gages
    network   (dict): Reverse connections graph
    path      (list): List of segments along search path
    node       (int): Stream segment under inquiry

    Returns:
    --------
    (bool): False if segment is a network break point, True otherwise

    '''
    if (path[-1] in gage_nodes) | (node in gage_nodes):
        return False  # force a path split if entering or exiting a waterbody
    else:
        return len(network[node]) == 1

def split_at_waterbodies_and_junctions(waterbody_nodes, network, path, node):
    '''
    Identify reach break points at waterbody inlets/outlets and junctions.

    Arguments:
    ----------
    waterbody_nodes (set): Nodes within waterbodies
    network        (dict): Reverse connections graph
    path           (list): List of segments along search path
    node            (int): Stream segment under inquiry

    Returns:
    --------
    (bool): False if segment is a network break point, True otherwise

    '''
    if (path[-1] in waterbody_nodes) ^ (node in waterbody_nodes):
        return False  # force a path split if entering or exiting a waterbody
    else:
        return len(network[node]) == 1


def dfs_decomposition_depth_tuple(RN, path_func, source_nodes=None):

    """
    Decompose network into lists of simply connected nodes
    For the routing problem, these sets of nodes are segments
    in a reach terminated by a junction, headwater, or tailwater.

    The function also identfies the network depth, by reach,
    of each reach and the output of the function is a list of tuples
    in the form: (network depth, [reach list]).
    The order of these reaches are suitable to be parallelized as
    we guarantee that
      1) for any segment withn a reach, the predecessor segments
      appear before it in the reach; and
      2) for any reach, the predecessor reaches appear before it
      in the main list.
    This is accomplished by a depth first search on the reversed
    graph. The depth first search function logs the path from
    each node to any network break defined by the `path_func`.
    The network depth is counted as the number of successive breaks.
    Arguments:
        N (Dict[obj: List[obj]]): The graph
        path_func: partial function defining the Network breaking function
        source_nodes: starting points (default use the top of the network,
        which, for the reversed network passed to this function,
        is the set of tailwaters...)

    Method:
      call dfs_decomposition
      call coalesce reaches
      call count order -- currently done with another dfs, but
        could be level order (i.e., bfs)
      zip results together and return order/reach tuples as before.

    Returns:
        [List(tuple)]: List of tuples of (depth, path) to be processed
        in order.
    """
    reach_list = dfs_decomposition(RN, path_func, source_nodes)

    # Label coalesced reaches with the hydrologcially  downstream-most segment
    tag_idx = -1

    RN_coalesced = coalesce_reaches(RN, reach_list, tag_idx)
    # Make sure that if source_nodes is not empty,
    # this doesn't create some kind of nasty collision.
    # TODO: There might be a way to more gracefully handle this...

    if source_nodes is None:
        source_nodes = headwaters(RN_coalesced)
    else:
        if source_nodes not in RN_coalesced:
            raise AssertionError(
                "the source nodes *must* be members of the coalesced set..."
            )
    depth_tuples = dfs_count_depth(RN_coalesced, source_nodes)
    return zip(pluck(0,depth_tuples), reach_list)


def dfs_count_depth(RN, source_nodes=None):
    """
    Returns tree depth, via depth-first-search of every element
    in a network.

    The count assumes that every element will be counted, so
    if the objective is to identify reach depth, the network
    must first be coalesced.
    """

    path_tuples = []
    reach_seq_order = 0
    visited = set()
    junctions = set()
    for h in source_nodes:
        stack = [(h, iter(RN[h]))]
        while stack:
            node, children = stack[-1]
            if node not in junctions:
                reach_seq_order += 1
                junctions.add(node)
            try:
                child = next(children)
                if child not in visited:
                    # Check to see if we are at a leaf
                    if child in RN:
                        stack.append((child, iter(RN[child])))
                    visited.add(child)
            except StopIteration:
                node, _ = stack.pop()

                reach_seq_order -= 1
                path_tuples.append((reach_seq_order, [node]))

    return path_tuples


def coalesce_reaches(RN, reach_list, tag_idx=-1):
    """
    From a list of reaches separated according to a particular rule
    (e.g., the rule might be, "split at junctions,"
    or "split at junctions_and waterbodies"),
    generate a new network describing the topology of the reaches
    using tag_idx to determine which segment id of the reach is
    used to represent the reach in the new topology.

    We assume that the RN is a reverse network and that the reaches are
    a forward network. Hydrologically,
    this means that the reaches are indexed from upstream to downstream
    but that the segment keys in the network give the ids of the
    upstream neighbors of each segment.

    The concept is extensible to a non-hydrologic network.

    Returns
    RN_coalesced which has the same form as RN (i.e., seg_key: [list, of, upstreams])
    but with each reach represented by exactly one topological element.
    """

    return {reach[tag_idx]: RN[reach[0]] for reach in reach_list}


def dfs_decomposition(N, path_func, source_nodes=None):
    """
    Decompose network into reaches - lists of simply connected segments.
    Reaches are sets of segments terminated by a junction, headwater, or tailwater.
    (... or other segments tagged by the `path_func`.)

    The order of the reaches returned are suitable to be parallelized as we guarantee that for any reach,
    the predecessor reaches appear before it in the list.

    This is accomplished by a depth first search on the reversed graph and
    finding the path from node to its nearest junction.

    Arguments:
    ----------
    N (dict {int: [int]}): Reverse network connections
    path_func (functools.partial): Function for identifying reach breaks
    source_nodes       (iterable): Segments from which to begin reach creation.
                                   defaults to network tailwater.

    Returns:
    (List): List of reaches to be processed in order.

    """

    if source_nodes is None:
        source_nodes = headwaters(N)

    paths = []
    visited = set()
    for h in source_nodes:
        stack = [(h, iter(N[h]))]
        while stack:
            node, children = stack[-1]
            try:
                child = next(children)
                if child not in visited:
                    # Check to see if we are at a leaf
                    if child in N:
                        stack.append((child, iter(N[child])))
                    visited.add(child)
            except StopIteration:
                node, _ = stack.pop()
                path = [node]

                for n, _ in reversed(stack):
                    if path_func(path, n):
                        path.append(n)
                    else:
                        break
                paths.append(path)
                if len(path) > 1:
                    # Only pop ancestor nodes that were added by path_func.
                    del stack[-(len(path) - 1) :]

    return paths

def kahn_toposort(N):
    degrees = in_degrees(N)
    zero_degree = set(k for k, v in degrees.items() if v == 0)

    _deg_pop = zero_degree.pop
    _deg_add = zero_degree.add
    _network_get = N.get
    while zero_degree:
        n = _deg_pop()
        for j in _network_get(n, ()):
            degrees[j] = c = degrees[j] - 1
            if c == 0:
                _deg_add(j)
        yield n

    try:
        next(degrees.elements())
        raise Exception("Cycle exists!")
    except StopIteration:
        pass


def reservoir_shore(connections, waterbody_nodes):
    wbody_set = set(waterbody_nodes)
    not_in = lambda x: x not in wbody_set

    shore = set()
    for node in wbody_set:
        shore.update(filter(not_in, connections[node]))
    return list(shore)


def reservoir_boundary(connections, waterbodies, n):
    if n not in waterbodies and n in connections:
        return any(x in waterbodies for x in connections[n])
    return False


def separate_waterbodies(connections, waterbodies):
    waterbody_nodes = {}
    for wb, nodes in reverse_surjective_mapping(waterbodies).items():
        waterbody_nodes[wb] = net = {}
        for n in nodes:
            if n in connections:
                net[n] = list(filter(waterbodies.__contains__, connections[n]))
    return waterbody_nodes


def replace_waterbodies_connections(connections, waterbodies):
    """
    Use a single node to represent waterbodies. The node id is the
    waterbody id. Create a cross walk dictionary that relates lake_ids
    to the terminal segments within the waterbody footprint.

    Arguments
    ---------
    - connections (dict):
    - waterbodies (dict): dictionary relating segment linkIDs to the
                          waterbody lake_id that they lie in

    Returns
    -------
    - new_conn  (dict): connections dictionary with waterbodies represented by single nodes.
                        Waterbody node ids are lake_ids
    - link_lake (dict): cross walk dictionary where keys area lake_ids and values are lists
                        of waterbody tailwater nodes (i.e. the nodes connected to the
                        waterbody outlet).
    """
    new_conn = {}
    link_lake = {}
    waterbody_nets = separate_waterbodies(connections, waterbodies)
    rconn = reverse_network(connections)

    for n in connections:
        if n in waterbodies:
            wbody_code = waterbodies[n]
            if wbody_code in new_conn:
                continue

            # get all nodes from waterbody
            wbody_nodes = [k for k, v in waterbodies.items() if v == wbody_code]
            outgoing = reservoir_shore(connections, wbody_nodes)
            new_conn[wbody_code] = outgoing

            link_lake[wbody_code] = list(set(rconn[outgoing[0]]).intersection(set(wbody_nodes)))[0]

        elif reservoir_boundary(connections, waterbodies, n):
            # one of the children of n is a member of a waterbody
            # replace that child with waterbody code.
            new_conn[n] = []

            for child in connections[n]:
                if child in waterbodies:
                    new_conn[n].append(waterbodies[child])
                else:
                    new_conn[n].append(child)
        else:
            # copy to new network unchanged
            new_conn[n] = connections[n]

    return new_conn, link_lake

def build_subnetworks(connections, rconn, min_size, sources=None):
    """
    Construct subnetworks using a truncated breadth-first-search

    Arguments:
        connections
        rconn
        max_depth
        sources
    Returns:
        subnetwork_master
    """
    # if no sources provided, use tailwaters
    if sources is None:
        # identify tailwaters
        sources = headwaters(rconn)

    # create a list of all headwaters in the network
    all_hws = headwaters(connections)

    subnetwork_master = {}
    for net in sources:

        # subnetwork creation using a breadth first search restricted by maximum allowable depth
        # new_sources_list = [net]
        new_sources = set([net])
        subnetworks = {}
        group_order = 0
        while new_sources:

            # Build dict object containing reachable nodes within max_depth from each source in new_sources
            rv = {}
            for h in new_sources:

                reachable = set()
                Q = deque([(h, 0)])
                stop_depth = 1000000
                while Q:

                    x, y = Q.popleft()
                    reachable.add(x)

                    rx = rconn.get(x, ())
                    if len(rx) > 1:
                        us_depth = y + 1
                    else:
                        us_depth = y

                    if len(reachable) > min_size:
                        stop_depth = y

                    if us_depth <= stop_depth:
                        Q.extend(zip(rx, [us_depth] * len(rx)))

                # reachable: a list of reachable segments within max_depth from source node h
                rv[h] = reachable

            # find headwater segments in reachable groups, these will become the next set of sources
            # new_sources_list = []
            new_sources = set()
            for tw, seg in rv.items():
                # identify downstream connections for segments in this subnetwork
                c = {key: connections[key] for key in seg}
                # find apparent headwaters, will include new sources and actual headwaters
                sub_hws = headwaters(c)
                # extract new sources by differencing with list of actual headwaters
                srcs = sub_hws - all_hws
                # append list of new sources
                new_sources.update(srcs)
                # remove new sources from the subnetwork list
                rv[tw].difference_update(srcs)

            # append master dictionary
            subnetworks[group_order] = rv

            # advance group order
            group_order += 1

        subnetwork_master[net] = subnetworks

    return subnetwork_master
