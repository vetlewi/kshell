#!/usr/bin/env python
import sys, os, os.path, shutil, readline, re
from fractions import Fraction
from typing import Tuple, List, Dict, TextIO
from ast import literal_eval
import gen_partition
from gen_partition import raw_input_save
from count_dim import count_dim

bindir = os.path.dirname( __file__ )    # Full path to the directory of this file.

# # Change the default behaviour by uncommenting the correct MPI preset.
# # The values listed can be chosen in the interactive setup even though
# # they are commented here.

is_mpi = False         # single node (w/o MPI)
#is_mpi = True         # FX10 
#is_mpi = 'fx10'       # FX10 
#is_mpi = 'coma'       # Tsukuba CCS COMA + sbatch
#is_mpi = 'k'          # K computer 'micro'
#is_mpi = 'k-micro'    # K computer 'micro'
#is_mpi = 'k-small'    # K computer 'small' queue with staging
#is_mpi = 'k-large'    # K computer 'large' queue with staging
#is_mpi = 'cx400'      # CX400 at Nagoya Univ.
#is_mpi = 'ofp'        # Oakforest-PACS at Tokyo and Tsukuba  
#is_mpi = 'ofp-flat'   # Oakforest-PACS at Tokyo and Tsukuba , flat mode
# is_mpi = "fram" # Fram cluster @ UiT, Norway

# NOTE: I (jonkd) removed global declaration of n_nodes from main.
# n_nodes = 24  # default number of MPI nodes 
# n_nodes = 768
# if is_mpi in ('k', 'k-micro', 'k-large'): n_nodes = 1152
# if is_mpi in ('cx400',): n_nodes = 4

GS_FREE_PROTON = 5.585
GS_FREE_NEUTRON = -3.826

var_dict = {
    "max_lanc_vec"  : 200 , 
    "maxiter"       : 300 , 
    "n_restart_vec" : 10 , 
    "hw_type"       : 1, 
    "mode_lv_hdd"   : 0, 
    "n_block"       : 0, 
    "eff_charge"    : [1.5, 0.5] , 
    "gl"            : [1.0, 0.0], 
    "gs"            : [GS_FREE_PROTON, GS_FREE_NEUTRON],
    # "gs"            : [0.9*GS_FREE_PROTON, 0.9*GS_FREE_NEUTRON],
    "beta_cm"       : 0.0, 
}

stgin_filenames  = [ 'kshell.exe', 'transit.exe', 'collect_logs.py', 'count_dim.py' ]
stgout_filenames = [ 'tmp_snapshot_*']

base_filename_list = []   # If several nuclides are specified. NOTE: Might be possible to remove this from the global scope.
snt_parameters = {} # Parameters will be read from the .snt file and put in this dictionary.

elements = [
    'NA', 
    'H',  'He', 'Li', 'Be', 'B',  'C',  'N',  'O',  'F',  'Ne', 
    'Na', 'Mg', 'Al', 'Si', 'P',  'S',  'Cl', 'Ar', 'K',  'Ca',
    'Sc', 'Ti', 'V',  'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
    'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y',  'Zr',
    'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
    'Sb', 'Te', 'I',  'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',
    'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',
    'Lu', 'Hf', 'Ta', 'W',  'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
    'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',
    'Pa', 'U',  'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm',
    'Md', 'No', 'Lr', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds',
    'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og'
]

class SimpleCompleter(object):
    def __init__(self, options):
        self.options = sorted(options)
        return

    def complete(self, text, state):
        response = None
        if state == 0:
            if text:
                self.matches = [s for s in self.options
                                if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        return response

readline.set_completer_delims('')

def split_jpn(jpn: str, valence_p_n: Tuple[int, int]) -> Tuple[int, int, int, bool]:
    """
    Take user input parity and number of states, along with the number
    of valence protons and neutrons and return a tuple of (spin, parity,
    number of states, is_jproj).

    Parameters
    ----------
    jpn:
        User input number of states, parity, and spins. Examples:
        '+100', '1.5-30'.

    valence_p_n:
        Tuple containing the number of valence protons and neutrons.

    Returns
    -------
    spin:
        2 times the spin of the state.

    parity:
        The parity of the state.

    n_states:
        The amount of states to be calculated with the given spin and
        parity.

    is_jproj:
        True if the spin is specified (ex: '1.5-30'), False if no spin
        is specified (ex: '+100').

    Examples
    --------
    list_jpn = [split_jpn(state, valence_p_n) for state in input_n_states]
    1.5-1, 3.5+3 for lowest one 3/2- states and three 7/2+ states)
    """
    idx = jpn.find("+")
    parity = 1
    arr = jpn.split("+")
    
    if idx == -1:
        """
        '+' not found, means that input is either for negative parity or
        invalid format.
        """
        idx = jpn.find("-")
        if idx == -1:
            msg = "Input state must have parity specified, but no parity was given."
            msg += f" Got {jpn=}"
            raise ValueError(msg)
        parity = -1
        arr = jpn.split("-")
    
    if arr[0]:
        """
        Spin is specified. Calculate the n lowest lying states with the
        given spin.
        
        Example: '3.5+3'.split('+') >>> ['3.5', '3']
        """
        is_jproj = True
    else:
        """
        Spin is not specified. Calculate the n lowest lying states.
        
        Example: '+10'.split('+') >>> ['', '10']
        """
        is_jproj = False

    if arr[0]:
        """
        Example: '1.5+3'.split('+') >>> ['1.5', '3'], thus arr[0] is the
        spin of the state(s) to be calculated.
        """
        spin = int(float(arr[0])*2) # Convert spin to 2*J.
    else:
        """
        Here, spin is always 0 or 1. TODO: Why?
        """
        spin = sum(valence_p_n)%2
    if arr[1]:
        """
        Example: '1.5+3'.split('+') >>> ['1.5', '3'], thus arr[1] is the
        number of states to be calculated.
        """
        n_states = int(arr[1]) 
    else:
        n_states = 10   # NOTE: Is this in use?
    
    return spin, parity, n_states, is_jproj
    
def create_base_filename(valence_p_n: tuple, model_space_filename: str) -> str:
    """
    Take in the number of valence protons and neutrons, along with the
    model space filename and create base filename for output script.
    Example output: 'O18_usda'.

    Parameters
    ----------
    valence_p_n:
        A tuple containing the number of valence protons and neutrons.

    model_space_filename:
        Example: 'usda.snt'.
    """
    core_protons, core_neutrons = snt_parameters['ncore']
    Z = abs(core_protons)
    # Z +=  valence_p_n[0] if core_protons>0 else -valence_p_n[0]
    if core_protons > 0:
        Z +=  valence_p_n[0]
    else:
        Z += -valence_p_n[0]
    
    mass = Z + abs(core_neutrons)
    
    if core_neutrons > 0:
        mass +=  valence_p_n[1]
    else:
        mass += -valence_p_n[1]

    return elements[Z] + str(mass) + "_" + model_space_filename[:-4]

def extract_valence_protons_and_neutrons(input_nuclide: str) -> tuple:
    """
    Convert atomic mass and element symbol (example: ['o18'], ['18o'])
    into tuple of valence protons and neutrons (example: (0, 2)).
    
    Parameters
    ----------
    input_nuclide:
        String of atomic mass + element symbol, example: ['o18'],
        ['18o'].
    """
    atomic_mass_match = re.search(r'\d+', input_nuclide)    # Match atomic mass.
    if not atomic_mass_match:
        """
        Regex gave no match.
        """
        print('\n *** Invalid: unknown element ***', input_nuclide)
        return False

    mass = int(atomic_mass_match.group()) # Extract atomic mass.
    element_symbol = input_nuclide[:atomic_mass_match.start()] + input_nuclide[atomic_mass_match.end():]   # Extract element symbol.
    element_symbol = element_symbol.lower()
    element_symbol = element_symbol[0].upper() + element_symbol[1:]  # Make element symbol capitalized.
    
    if not element_symbol in elements:
        print('*** Invalid: unknown element ***', element_symbol)
        return False
    
    z = elements.index(element_symbol)
    corep, coren = snt_parameters['ncore']
    
    if corep > 0: nf1 =  z - corep
    else:         nf1 = -z - corep
    if coren > 0: nf2 =   mass - z  - coren
    else:         nf2 = -(mass - z) - coren
        
    print('\n number of valence particles ', nf1, nf2)
    
    if nf1 < 0 or nf2 < 0 or \
       nf1 > snt_parameters['nfmax'][0] or \
       nf2 > snt_parameters['nfmax'][1]:
        print('*** ERROR: nuclide out of model space ***')
        return False
    return (nf1, nf2)
    
def print_var_dict(var_dict, skip=()):
    """
    Convert the dictionary containing simulation parameters ('var_dict')
    into a single string.

    Parameters
    ----------
    var_dict : dictionary
        The dictionary containing simulation parameters. Defined at the
        beginning of this file and possibly modified in the interactive
        user interface.

    skip : tuple, list
        A list or tuple of keys to skip.

    Returns
    -------
    ret : string
        A string representation of the entire dictionary without the
        keys defined in 'skip'.
    """
    ret = ""
    keys = var_dict.keys()

    for key in sorted(keys):
        if key in skip: continue
        v = var_dict[key]
        if isinstance(v, list): 
            """
            Example: {..., "eff_charge": [1.5, 0.5], ...}
            """
            vv = ""
            for i in v: vv += str(i) + ", "
        elif isinstance(v, int) or isinstance(v, float):
            """
            Example: {..., "n_restart_vec": 10, ...}
            """
            vv = str(v)
        else: vv = v
        ret += "  " + key + " = " + vv + "\n"
    return ret

def prty2str(p):
    """
    Convert numeric parity representation to string representation.

    Parameters
    ----------
    p : int
        Parity. Valid inputs are 1, -1.

    Returns
    -------
    : string
        'p' if input parity is 1, 'n' if input parity is -1.

    Raises
    ------
    ValueError
        If input is anything other than 'p' or 'n'.
    """
    if p == 1: return "p"
    elif p == -1: return "n"
    else: raise ValueError("Parity must be 1 or -1.")

def read_comment_skip(model_space_file: TextIO) -> List:
    """
    Extract model space data and recommended parameters from .snt file.
    Enter the recommended parameters into var_dict.
    Example from jun45.snt:
    ! default input parameters 
    !namelist eff_charge = 1.5, 1.1
    !namelist gl         = 1.0, 0.0 
    !namelist gs         = 3.910, -2.678 
    !namelist orbs_ratio = 4, 8
    !
    ! model space
    4   4    28  28
    1       1   1   3  -1    !  1 = p 1p_3/2
    2       0   3   5  -1    !  2 = p 0f_5/2
    3       1   1   1  -1    !  3 = p 1p_1/2
    4       0   4   9  -1    !  4 = p 0g_9/2
    5       1   1   3   1    !  5 = n 1p_3/2
    6       0   3   5   1    !  6 = n 0f_5/2
    7       1   1   1   1    !  7 = n 1p_1/2
    8       0   4   9   1    !  8 = n 0g_9/2

    Parameters
    ----------
    model_space_file : TextIO
        File object of the .snt file.
    """
    header_printed = False  # To print recommended parameters header only once.
    while True:
        line = model_space_file.readline().split()
        if not line: return None    # NOTE: When does this happen?
        
        if line[0] == '!namelist':
            """
            Extract recommended parameters from .snt file. For example
            eff_charge, gl, gs, orbs_ratio. Example:
            
            ! default input parameters 
            !namelist eff_charge = 1.5, 1.1
            !namelist gl         = 1.0, 0.0 
            !namelist gs         = 3.910, -2.678 
            !namelist orbs_ratio = 4, 8
            """
            if line[2] != '=':
                """
                Second element in '!namelist' line should always be '='.
                """
                msg = "!namelist syntax error in .snt file.\n"
                msg += f"{line = }"
                raise ExternalSyntaxError(msg)

            var_dict[line[1]] = ' '.join(line[3:])  # Update entries with recommended values.
            if not header_printed:
                msg = "\nRecommended parameters extracted from .snt and saved"
                msg += " in var_dict: "
                print(msg)
                header_printed = True

            if f"{line[1]}" == "gs":
                """
                Calculate the quenching factor in addition to displaying
                the gs values.
                """
                tmp = literal_eval(var_dict[line[1]])
                gs_proton = float(tmp[0])
                gs_neutron = float(tmp[1])
                proton_quench = round(gs_proton/GS_FREE_PROTON, 1)
                neutron_quench = round(gs_neutron/GS_FREE_NEUTRON, 1)
                print(f"{line[1]} = {var_dict[line[1]]} (quench: {proton_quench}, {neutron_quench})")
            else:
                print(f"{line[1]} = {var_dict[line[1]]}")
        
        for i in range(len(line)):
            """
            Loop over all elements in 'line' and extract model space
            info. Example:
            ! model space
            4   4    28  28
            1       1   1   3  -1    !  1 = p 1p_3/2
            2       0   3   5  -1    !  2 = p 0f_5/2
            3       1   1   1  -1    !  3 = p 1p_1/2
            4       0   4   9  -1    !  4 = p 0g_9/2
            5       1   1   3   1    !  5 = n 1p_3/2
            6       0   3   5   1    !  6 = n 0f_5/2
            7       1   1   1   1    !  7 = n 1p_1/2
            8       0   4   9   1    !  8 = n 0g_9/2
            """
            if (line[i][0] == "!") or (line[i][0] == "#"):
                """
                Slice away info after comment symbol. From the example
                above, '!  1 = p 1p_3/2' will be removed.
                """
                line = line[:i]
                break

        if not line: continue
        
        try:
            """
            Example: 4   4    28  28
            """
            return [int(i) for i in line]
        except ValueError:
            """
            NOTE: When does this ever happen? I have checked all the
            built-in .snt files that come with KSHELL and none of them
            trigger this ValueError.
            """
            try:
                return [int(i) for i in line[:-1]] + [float(line[-1])]
            except ValueError:
                return line

class ExternalSyntaxError(Exception):
    """
    Raised when there is a syntax error in any of the data files
    associated with KSHELL.
    """
    pass

def read_snt(model_space_filename: str):
    """
    Read model space file (.snt), extract information about orbit
    properties (occupation, angular momentum, etc.) and save in
    snt_parameters dictionary.

    Parameters
    ----------
    model_space_filename : str
        Path to .snt file.
    """
    infile = open(model_space_filename, 'r')
    n_valence_orbitals_proton, n_valence_orbitals_neutron, n_core_protons, n_core_neutrons = \
        read_comment_skip(infile)
    norb = []   # ?
    lorb = []   # Orbital angular momentum.
    jorb = []   # Orbital angular momentum z projection.
    torb = []   # Orbital isospin.
    npn = [n_valence_orbitals_proton, n_valence_orbitals_neutron]  # NOTE: Not in use.
    nfmax = [0, 0]  # Max number of valence protons and neutrons.
    
    for i in range(n_valence_orbitals_proton + n_valence_orbitals_neutron):
        """
        Extract model space information from .snt file. Example from
        jun45.snt:
        ! model space
            4   4    28  28
            1       1   1   3  -1    !  1 = p 1p_3/2
            2       0   3   5  -1    !  2 = p 0f_5/2
            3       1   1   1  -1    !  3 = p 1p_1/2
            4       0   4   9  -1    !  4 = p 0g_9/2
            5       1   1   3   1    !  5 = n 1p_3/2
            6       0   3   5   1    !  6 = n 0f_5/2
            7       1   1   1   1    !  7 = n 1p_1/2
            8       0   4   9   1    !  8 = n 0g_9/2
        """
        arr = read_comment_skip(infile)
        
        if (i + 1) != int(arr[0]):
            """
            All valence orbitals are labeled 1 to N. Raise error if the
            numbering is not 1, 2, 3, ..., N.
            """
            msg = f"Syntax error in {model_space_filename}. Expected {i + 1} got {arr[0]}."
            raise ExternalSyntaxError(msg)

        norb.append( int(arr[1]) )
        lorb.append( int(arr[2]) )
        jorb.append( int(arr[3]) )
        torb.append( int(arr[4]) )
        nfmax[(int(arr[4]) + 1)//2] += int(arr[3]) + 1

    infile.close()
    snt_parameters['ncore'] = (n_core_protons, n_core_neutrons)   # Number of protons and neutrons in the core.
    snt_parameters['n_jorb'] = (n_valence_orbitals_proton, n_valence_orbitals_neutron)
    snt_parameters['norb'] = norb
    snt_parameters['lorb'] = lorb          # Angular momentum of each orbit.
    snt_parameters['jorb'] = jorb          # z proj. of total spin of each orbit.
    snt_parameters['torb'] = torb          # Isospin of each orbit (proton or neutron).
    snt_parameters['nfmax'] = nfmax
    
def check_cm_snt(model_space_filename):
    # return whether Lawson term is required or not
    is_cm = False
    nc = snt_parameters['ncore']
    if nc[0] < 0 or nc[1] < 0: return
    npn = snt_parameters['n_jorb']
    for np in range(2):
        p_list, j_list = [], []
        for i in range(npn[np]):
            p_list.append( 1 - (snt_parameters['lorb'][i] % 2)*2 )
            j_list.append( snt_parameters['jorb'][i] )
        j_list_posi = [j for p, j in zip(p_list, j_list) if p == 1]
        j_list_nega = [j for p, j in zip(p_list, j_list) if p == -1]
        for jp in j_list_posi:
            for jn in j_list_nega:
                if abs(jp-jn) <= 2: is_cm = True        
    return is_cm

def exec_string(mode: str, input_filename: str, log_filename: str) -> str:
    """
    Generate the execution command. Example:
    mpiexec ./kshell.exe O20_usda_0.input > log_O20_usda_j0p.txt

    Parameters
    ----------
    mode : str
        Mode is either 'kshell' or 'transit'.

    input_filename : str
        The filename of the Fortran input parameter file (the values in
        var_dict).

    log_filename : str
        The filename of the output logfile from the Fortran code (kshell
        or transit).
    """
    exec_command = ' ./' + mode + '.exe '
        
    if is_mpi in ('coma', 'cx400'): 
        return 'mpirun ' + exec_command + input_filename + ' > ' + log_filename + '  \n\n'
    elif is_mpi in ('ofp-flat', ):
        return r'mpiexec.hydra  -n ${PJM_MPI_PROC} numactl --preferred=1 ' \
            + exec_command + input_filename + ' > ' + log_filename + '  \n\n'
    elif is_mpi in ('ofp', ):
        return r'mpiexec.hydra  -n ${PJM_MPI_PROC} ' + exec_command + input_filename + ' > ' + log_filename + '  \n\n'
    elif is_mpi == 'fram': 
        return 'mpiexec' + exec_command + input_filename + ' > ' + log_filename + '  \n\n'
    elif is_mpi == 'betzy': 
        return f"mpiexec{exec_command}{input_filename} > {log_filename}  \n\n"
        # return 'mpiexec' + exec_command + input_filename + ' > ' + log_filename + '  \n\n'
    elif is_mpi:
        return 'mpiexec -of ' + log_filename + exec_command + input_filename + ' \n\n'
    else:
        return 'nice' + exec_command + input_filename + ' > ' + log_filename + ' 2>&1 \n\n'

def output_transit(base_filename, input_filename, fn_wav_ptn1, fn_wav_ptn2, jpn1, jpn2):
    m1, np1, ne1, isj1 = jpn1
    m2, np2, ne2, isj2 = jpn2

    def list2str( a ):
        if isinstance(a, list): 
            return str(a[0])+', '+str(a[1])
        else: return a
    eff_charge = list2str( var_dict[ "eff_charge" ] )
    gl = list2str( var_dict[ "gl" ] )
    gs = list2str( var_dict[ "gs" ] )

    out = ""
    if isj1: jchar1 = '_j'
    else:    jchar1 = '_m'
    if isj2: jchar2 = '_j'
    else:    jchar2 = '_m'
    log_filename = 'log_' + base_filename + '_tr' \
        + jchar1 + str(m1) + prty2str(np1) \
        + jchar2 + str(m2) + prty2str(np2) + '.txt'
    stgout_filenames.append( log_filename )

    out += 'echo "start running ' + log_filename + ' ..."\n' 
    out += 'cat > ' + input_filename + ' <<EOF\n' \
        +  '&input\n'
    out += '  fn_int   = ' + var_dict["fn_int"] + '\n' \
        +  '  fn_ptn_l = ' + fn_wav_ptn1[1] + '\n' \
        +  '  fn_ptn_r = ' + fn_wav_ptn2[1] + '\n' \
        +  '  fn_load_wave_l = ' + fn_wav_ptn1[0] + '\n' \
        +  '  fn_load_wave_r = ' + fn_wav_ptn2[0] + '\n' \
        +  '  hw_type = ' + str(var_dict["hw_type"]) + '\n' \
        +  '  eff_charge = ' + eff_charge + '\n' \
        +  '  gl = ' + gl + '\n' \
        +  '  gs = ' + gs + '\n' 
    if 'is_obtd' in var_dict: 
        out += '  is_obtd = ' + str(var_dict['is_obtd']) + '\n'
    out += '&end\n' \
        +  'EOF\n'

    out +=  exec_string('transit', input_filename, log_filename)

    return out

def main_nuclide(
    model_space_filename: str
    ) -> Tuple[str, str, Tuple[int, int], List[Tuple[int, int, int, bool]], Dict[tuple, str]]:
    """
    Prompt for nuclide, number of states to calculate, truncation, and
    parameter adjustment.

    Parameters
    ----------
    model_space_filename:
        Example: 'usda.snt'.

    Returns
    -------
    base_filename:
        The base filename used for logs, summary, main script and
        partition files. Example: 'Ar28_usda'.

    shell_file_content_single:
        The content of the executable shell file for a single nucleon.

    valence_p_n:
        A tuple containing the number of valence protons and neutrons.
    
    list_jpn:
        A list containing tuples with the 2*spin, parity, number of
        states, and is_jproj for each requested state to be calculated.

    fn_save_dict:
        A dictionary where the keys are each tuple from list_jpn, and
        the values are the corresponding .wav and .ptn files.

    """
    print("\n\n*************** specify a nuclide ********************\n")

    main_nuclide_msg = "\n number of valence protons and neutrons\n"
    main_nuclide_msg += "(ex.  2, 3 <CR> or 9Be <CR>)    <CR> to quit : "
    main_nuclide_syntax_msg = "Nuclide input must be of the syntax: '#p', '#p, #n', 'AX', 'XA'"
    
    while True:
        """
        Prompt for nuclide information.
        """
        input_nuclide_or_valence = raw_input_save(main_nuclide_msg)
        input_nuclide_or_valence = input_nuclide_or_valence.replace(',', ' ').split()   # TODO: Maybe just .split(",")? No, then it does not support values separated by whitespace.
        if len(input_nuclide_or_valence) == 0:
            """
            No input.
            """
            return "", "", None, None, None
        
        elif len(input_nuclide_or_valence) == 1:
            """
            Example: ['o18'], ['18o'], ['5'].
            """
            if input_nuclide_or_valence[0].isdigit():
                """
                Assume only number of valence protons is given. Append
                the default number of valence neutrons (0).
                Example: ['5'].
                """
                valence_p_n = [int(input_nuclide_or_valence[0]), 0]
            else:
                """
                Example: ['o18'], ['18o'] or something else entirely,
                like ['uptheirons!'].
                """
                valence_p_n = extract_valence_protons_and_neutrons(input_nuclide_or_valence[0])
                if not valence_p_n:
                    print(main_nuclide_syntax_msg)
                    continue
        
        elif len(input_nuclide_or_valence) == 2:
            valence_p_n = [int(input_nuclide_or_valence[0]), int(input_nuclide_or_valence[1])]

        else:
            print(main_nuclide_syntax_msg)
            continue
        
        break

    base_filename = create_base_filename(valence_p_n, model_space_filename)
    while base_filename in base_filename_list:
        """
        If the same nuclide is specified several times, an 'x' is
        inserted into the script filename to differentiate between them.
        """
        n = len(model_space_filename) - 3
        base_filename = base_filename[:-n] + 'x' + base_filename[-n:]

    input_base_filename = raw_input_save("\n name for script file (default: " + base_filename + " ): ")
    input_base_filename = input_base_filename.strip()
    if input_base_filename: base_filename = input_base_filename
    base_filename_list.append( base_filename )

    default_states = 10
    print("\n J, parity, number of lowest states  ")
    print(f"  (ex. {default_states:d}          for {default_states:d} +parity, {default_states:d} -parity states w/o J-proj. (default)")
    print("       -5           for lowest five -parity states, ")
    print("       0+3, 2+1     for lowest three 0+ states and one 2+ states, ")
    print("       1.5-1, 3.5+3 for lowest one 3/2- states and three 7/2+ states) :")

    input_n_states = raw_input_save()
    input_n_states = input_n_states.replace(',', ' ').split()
    
    if not input_n_states:
        """
        If no input is given, go to default values.
        """
        input_n_states = [f'+{default_states:d}', f'-{default_states:d}']
    
    if (len(input_n_states) == 1) and (input_n_states[0].isdigit()):
        """
        If only the number of states is specified, not parity. Example:
        '100'. Then 100 + and - states are chosen.
        """
        input_n_states = ['+' + input_n_states[0], '-' + input_n_states[0]]
    
    list_jpn = [split_jpn(state, valence_p_n) for state in input_n_states]

    n_removed = 0
    for j, p, n, isp in list_jpn:
        if (j + sum(valence_p_n))%2 != 0:
            """
            If the sum of valence nucleons plus 2 times the spin of the
            state is not divisible by 2, then it is not a valid spin for
            this number of nucleons.
            """
            n_removed += 1
            if n_removed == 1:
                msg = "\nRemoving invalid states:\n"
                msg += "spin   parity   n states   isp\n"
                msg += "--------------------------------"
                print(msg)

            p = "+" if p == 1 else "-"
            print(f"{str(Fraction(j/2)):4}      {p:1}      {n:4}      {str(isp):5}")
    
    list_jpn = [a for a in list_jpn if (a[0] + sum(valence_p_n))%2 == 0]    # Remove invalid states as described a few lines above. TODO: Include this in the above loop.

    parity_list = list( set( jpn[1] for jpn in list_jpn ) )   # Extract a list of only parities. Might at this point contain a parity not supported by the model space.
    fn_ptn_list = {-1:base_filename + "_n.ptn", 1:base_filename + "_p.ptn"}
    trc_list_prty = {-1:None, 1:None}

    for parity in parity_list:
        """
        Generate partition file(s).
        """
        partition_filename = fn_ptn_list[parity]
        if parity == 1: 
            print('\n truncation for "+" parity state in ', partition_filename)
        else:          
            print('\n truncation for "-" parity state in ', partition_filename)

        trc_list_prty[parity] = gen_partition.main(model_space_filename, partition_filename, valence_p_n, parity)

        if os.path.exists( partition_filename ): stgin_filenames.append( partition_filename )

    #-----------------------------------------------------
    list_param = [ k +" = " for k in var_dict.keys() ]
    list_param += [ # A few extra tab complete entries.
        'is_obtd = .true.', 'is_ry_sum = .true.', 'is_calc_tbme = .true.',
        'sq = ', 'quench = '
    ]
    parameter_info = "\nModify parameters?\n"
    parameter_info += "Example: maxiter = 300 for parameter change or <CR> for no more"
    parameter_info += " modification.\nAvailable paramters are:\n"
    print(f"{parameter_info}{[i.split(' = ')[0] for i in list_param]}\n")
    
    readline.set_completer( SimpleCompleter(list_param).complete )
    if 'libedit' in readline.__doc__: # for Mac
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
    # readline.parse_and_bind("tab: None")
    while True:
        """
        Update parameters in var_dict.
        """
        print("\n --- set parameters --- ")
        print(print_var_dict(
            var_dict,
            skip = (    # NOTE: 'fn_ptn' and 'partition_filename' mixup.
                'fn_int', 'fn_save_wave', 'n_eigen', 'fn_ptn', 'is_double_j',
                'mtot'
            )
        ))

        ans = raw_input_save(": ")
        ans = ans.strip()
        if not ans:
            """
            Stop asking for parameters if no parameter is given.
            """
            break
        
        elif '=' in ans:
            """
            Update entry in var dict if input is given on the form
            'name = value' (with or without whitespaces).
            """
            arr = ans.split('=')
            arr = [a.strip() for a in arr]    # Remove whitespaces, but keep whitespace entries.
            if len(arr[1]) != 0:
                """
                If a value is given for 'name', then update 'name' in
                var_dict.
                """
                if (arr[0] == "sq") or (arr[0] == "quench"):
                    """
                    Specify a quenching factor which is multiplied with
                    the free gs values for protons and neutrons. The
                    quenching factor itself is not an entry in var_dict.
                    """
                    gs_quenching_factor = float(arr[1])
                    print(f"Quenching of spin g-factor: {gs_quenching_factor}*GS_FREE")
                    var_dict["gs"] = [
                        round(gs_quenching_factor*GS_FREE_PROTON, 3),
                        round(gs_quenching_factor*GS_FREE_NEUTRON, 3)
                    ]
                else:
                    var_dict[arr[0]] = arr[1]
            else:
                """
                If input is 'name = ', then 'name' is removed if it
                exists.
                """
                try:
                    del var_dict[arr[0]]
                except KeyError:
                    msg = f"No entry for input parameter {arr[0]}"
                    print(msg)
            
            continue

        else:
            msg = "Input must be on the form: 'name = value'."
            msg += " <CR> to proceed, TAB to complete."
            print(msg)
            continue

    # ---------------------------------------------

    shell_file_content_single = '# ---------- ' + base_filename + ' --------------\n'
    list_jpn = [ jpn for jpn in list_jpn if os.path.isfile( fn_ptn_list[ jpn[1] ]) ]    # Checks that the correct .ptn file exists.
    fn_save_dict = {}
    
    for mtot, nparity, n_eigen, is_proj in list_jpn:
        if is_proj:
            """
            Specific spin(s) requested.
            """
            jchar = '_j'
            var_dict[ 'is_double_j' ] = '.true.'
        else:
            """
            No specific spin(s) requested, only a number of the lowest
            laying states.
            """
            jchar =  '_m'
            var_dict[ 'is_double_j' ] = '.false.'
        var_dict[ 'fn_ptn' ] = '"' + fn_ptn_list[nparity] + '"' # NOTE: 'fn_ptn' and 'partition_filename' mixup.

        if (trc_list_prty[nparity] is not None) and (not 'orbs_ratio' in var_dict.keys()):
            var_dict[ 'orbs_ratio' ] = trc_list_prty[nparity]

        wave_filename = \
            f"{base_filename}{jchar}{str(mtot)}{prty2str(nparity)}.wav"
        # fn_save_wave = base_filename + jchar + str(mtot) + prty2str(nparity) + '.wav'

        stgout_filenames.append( wave_filename )
        # wave_filename = '"' + wave_filename + '"'
        wave_filename = f'"{wave_filename}"'
        log_filename = \
            f"log_{base_filename}{jchar}{str(mtot)}{prty2str(nparity)}.txt"
            # 'log_' + base_filename + jchar + str(mtot) + prty2str(nparity) + '.txt'
        stgout_filenames.append( log_filename )
        var_dict[ 'fn_save_wave' ] = wave_filename
        fn_save_dict[ (mtot, nparity, n_eigen, is_proj) ] \
            = wave_filename, var_dict[ 'fn_ptn' ]    # NOTE: 'fn_ptn' and 'partition_filename' mixup.
        var_dict[ 'n_eigen' ] = n_eigen
        var_dict[ 'n_restart_vec' ] \
            = max( int(n_eigen * 1.5) , int(var_dict[ 'n_restart_vec' ]) )
        var_dict[ "max_lanc_vec" ] \
            = max( var_dict[ 'max_lanc_vec' ], 
                   int(var_dict[ 'n_restart_vec' ]) + 50 )
        var_dict[ 'mtot' ] = mtot
        
        # input_filename = base_filename + '_' + str(mtot) + '.input'
        input_filename = f"{base_filename}_{str(mtot)}.input"

        if 'no_save' in var_dict.keys():
            del var_dict[ 'fn_save_wave' ]

        shell_file_content_single += 'echo "start running ' + log_filename + ' ..."\n' 
        shell_file_content_single += 'cat > ' + input_filename + ' <<EOF\n' \
            +  '&input\n'
        shell_file_content_single += print_var_dict( var_dict, skip=('is_obtd', 'no_save') )
        shell_file_content_single += '&end\n' \
            +  'EOF\n'
        
        shell_file_content_single +=  exec_string('kshell', input_filename, log_filename)

        partition_filename = fn_ptn_list[nparity]

        shell_file_content_single += 'rm -f tmp_snapshot_' + partition_filename + '_' + str(mtot) + '_* ' + \
               'tmp_lv_' + partition_filename + '_' + str(mtot) + '_* ' + \
               input_filename + ' \n\n\n'

        # if var_dict.has_key('orbs_ratio'): del var_dict[ 'orbs_ratio' ]

    transition_prob_msg = f"Compute transition probabilities (E2/M1/E1) for"
    transition_prob_msg += f" {base_filename} ? Y/N (default: Y)"
    print(transition_prob_msg)
    while True:
        ans = raw_input_save(": ")
        try:
            if ans[0].lower() == "y": is_transit = True
            elif ans[0].lower() == "n": is_transit = False
            else: continue
        except IndexError:
            """
            [0] does not exist because no input was given. Revert to
            default value.
            """
            is_transit = True   # Default.
            break
        break
        
    if is_transit: 
        is_e2m1, is_e1 = True,  True
        shell_file_content_single += "# --------------- transition probabilities --------------\n\n"
    else: 
        is_e2m1, is_e1 = False, False
    
    parity_list = list( set( jpn[1] for jpn in list_jpn ) ) # Contains only the supported parity / parities.
    if len(parity_list) < 2:
        """
        If parity_list only contains a single parity, then no transit
        will have a change of parity and thus E1 is impossible.
        """
        is_e1 = False

    """
    list_jpn:
        A list containing tuples with the 2*spin, parity, number of
        states, and is_jproj for each requested state to be calculated.
    """

    for idx_1, (spin_1, parity_1, n_states_1, is_jproj_1) in enumerate(list_jpn):
        for idx_2, (spin_2, parity_2, n_states_2, is_jproj_2) in enumerate(list_jpn):
            """
            Loop over all pairs of transitions. Some might be skipped
            due to gramma transition rules.
            """
            is_skip = True
            
            if idx_1 > idx_2:
                """
                Use each unordered spin pair only once. Skip (1, 0) if
                (0, 1) has already occurred.
                """
                continue
            
            if (is_jproj_1 and (spin_1 == 0)) and (is_jproj_2 and (spin_2 == 0)):
                """
                0 to 0 transitions are not allowed. But why demand that
                is_jproj is True?
                """
                continue
            
            if is_e2m1:
                if abs(spin_1 - spin_2) <= 4 and (parity_1 == parity_2):
                    """
                    If the spin difference between two orbitals is 2 or
                    1, and there is no change in parity, then E2 and M1
                    transitions are allowed (remember that spin_1 and
                    spin_2 are twice the spin).

                    NOTE: This check allows the difference to be 0, but
                    0 transitions are not allowed so they must be
                    excluded somewhere else. NOTE in the note: if the
                    difference is 0 (for example 2 -> 2), then the
                    transition might still happen with L = 1, 2 (and
                    theoretically 3, 4 but this is not supported by
                    KSHELL).
                    """
                    is_skip = False
            if is_e1:
                if abs(spin_1 - spin_2) <= 2 and (parity_1 != parity_2):
                    """
                    If the spin difference between two orbitals is 1,
                    and there is a change in parity, then E1 transitions
                    are allowed.
                    """
                    is_skip = False
            
            if is_skip:
                """
                Skip any transition which do not pass the above two
                tests.
                """
                continue
            
            # input_filename = base_filename + '_' + str(spin_1) + '_' + str(spin_2) + '.input'
            input_filename = f"{base_filename}_{str(spin_1)}_{str(spin_2)}.input"
            shell_file_content_single += output_transit(
                base_filename,
                input_filename,
                fn_save_dict[(spin_1, parity_1, n_states_1, is_jproj_1)],
                fn_save_dict[(spin_2, parity_2, n_states_2, is_jproj_2)],
                (spin_1, parity_1, n_states_1, is_jproj_1),
                (spin_2, parity_2, n_states_2, is_jproj_2)
            )
            # shell_file_content_single += 'rm -f ' + input_filename + '\n\n\n'
            shell_file_content_single += f"rm -f {input_filename}\n\n\n"

    # summary_filename = 'summary_' + base_filename + '.txt'
    summary_filename = f"summary_{base_filename}.txt"
    stgout_filenames.append(summary_filename)
    # shell_file_content_single += "./collect_logs.py log_*" + base_filename + "* > " + summary_filename + "\n"
    shell_file_content_single += f"./collect_logs.py log_*{base_filename}* > {summary_filename}\n"
    # shell_file_content_single += 'rm -f tmp_snapshot_' + base_filename + '* tmp_lv_' + base_filename + '* ' \
    #       + input_filename + ' \n'
    # shell_file_content_single += 'echo "Finish computing ' + base_filename + '.    See ' + summary_filename + '"\n'
    # shell_file_content_single += 'echo \n\n'
    shell_file_content_single += f'echo "Finish computing {base_filename}. See {summary_filename}"\necho\n\n'

    return base_filename, shell_file_content_single, valence_p_n, list_jpn, fn_save_dict

def ask_yn(optype):
    ret = False
    ans = raw_input_save( \
        '\n compute ' + optype + '? Y/N (default: No) : ')
    if len(ans) >0:
        if ans[0] == 'Y' or ans[0] == 'y': ret = True
        if ans[0] == 'N' or ans[0] == 'n': ret = False
    return ret

def check_j_scheme_dimensionality(
    states: list,
    model_space_filename: str,
    shell_file_content_total: str
    ):
    """
    Check that the requested amount of states does not exceed the
    J-scheme dimensionality.
    """
    msg = "\nChecking whether the requested number of energy eigenstates"
    msg += " exceeds the J-scheme dimensionality..."
    print(msg)
    for state in states:
        """
        Loop over all the requested states. Correct the number of
        requested energy eigenstates, if needed.
        """
        partition_filename = state[6][1].replace('"', '')
        wave_filename = state[6][0].replace('"', '')
        M, _, jdim = count_dim(
            model_space_filename = model_space_filename,
            partition_filename = partition_filename,
            print_dimensions = False
        )
        _, spin, parity, n_states, is_jproj, _, _ = state
        parity = "+" if parity == +1 else "-"

        if not is_jproj:
            """
            The number of states requested is not for a specific spin.
            TODO: Sum up all the J-scheme dims and check that?
            """
            continue

        for i in range(len(M)):
            if (M[i] == spin) and (n_states > jdim[i]):
                """
                If 'n_states' is greater than 'jdim[i]' then the number
                of requested states exceeds the J-scheme dimensionality.
                In that case, the first occurrence of .wav filename is
                located and the first occurrence of 'n_eigen' after this
                is changed to the maximum allowed number of states for
                the given spin. .wav filename is located first since the
                first occurrence of 'n_eigen' after this must be the
                correct occurence of 'n_eigen' to change.
                """
                msg = f"{partition_filename.split('_')[0]}:"
                msg += f" Changing {spin/2:.0f}{parity} from {n_states} to {jdim[i]}."
                idx = shell_file_content_total.find(wave_filename)
                shell_file_content_total = \
                    shell_file_content_total[:idx] + \
                    shell_file_content_total[idx:].replace(
                        f"n_eigen = {n_states}",
                        f"n_eigen = {jdim[i]}",
                        1
                    )
                print(msg)

    print("Done!\n")
    
    return shell_file_content_total

def main():
    print("\n")
    print("----------------------------- \n")
    print("  KSHELL user interface \n")
    print("     to generate job script. \n")
    print("-----------------------------\n ")

    cdef = 'N'  # Default MPI parallel value.
    n_nodes = 64    # Default value. May be overwritten.
    global is_mpi
    if is_mpi: cdef = is_mpi
    if cdef == True: cdef = 'Y'
    list_param = [  # Valid MPI parameters.
        'coma', 'fx10', 'k', 'k-micro', 'k-small', 'k-large', 'cx400',
        'ofp', 'ofp-flat', 'oakforest-pacs', 'yes', 'no', 'Y', 'N', 'y',
        'n', 'Yes', 'No', ''
    ]
    # Sigma2 specifics:
    list_param += ['fram', 'betzy']  # Added by jonkd.
    n_tasks_per_node = 8    # The number of MPI ranks per node. Default value. May be overwritten.
    n_cpus_per_task = 16    # The number of OpenMP threads per MPI rank. Default value. May be overwritten.
    
    type_of_fram_jobs_list = ["normal", "short", "devel"]
    fram_job_node_limits = {
        "normal": [1, 32],
        "short": [1, 10],
        "devel": [1, 8]
    }
    fram_job_description = {
        "normal": "Normal. Nodes: 1 to 32, priority: normal, maximum walltime: 7 days",
        "short": "Short. Nodes: 1 to 10, priority: high (slightly lower than devel), maximum walltime: 2 hours",
        "devel": "Devel. Nodes: 1 to 8, priority: high, maximum walltime: 30 minutes"
    }
    type_of_betzy_jobs_list = ["normal", "preproc", "devel"]
    betzy_job_node_limits = {
        "normal": [4, 512],
        "preproc": [1, 16],
        "devel": [1, 4]
    }
    betzy_job_description = {
        "normal": "Normal. Nodes: 4 to 512, priority: normal, maximum walltime: 4 days",
        "preproc": "Preproc. Units: 1 to 16, priority: normal, maximum walltime: 1 day",
        "devel": "Devel. Nodes: 1 to 4, priority: high, maximum walltime: 60 minutes"
    }
    
    readline.set_completer( SimpleCompleter(list_param).complete )
    readline.parse_and_bind("tab: complete")
    
    while True:
        """
        Fetch MPI input from user. Valid inputs are 'Y/N/preset', and
        'Y/N/preset, number of nodes'.
        """
        mpi_input_ans = raw_input_save( 
            '\n MPI parallel? Y/N/preset, n nodes (default: ' + cdef + ',  TAB to complete) : '
        )
        mpi_input_arr = mpi_input_ans.replace(',', ' ').split() # Example input: 'y, 10'.
        if not mpi_input_arr:
            """
            Revert to default (cdef) if no input is given.
            """
            mpi_input_arr = [ cdef, ]
        if mpi_input_arr[0] in list_param:
            if (len(mpi_input_arr) == 1) or (mpi_input_arr[1].isdigit()): break
        print("\n *** Invalid input ***")

    if (mpi_input_ans.split(",")[0] == "fram") or (mpi_input_ans.split(",")[0] == "betzy"):
        """
        Fetch Fram / Betzy Slurm input parameters. Added by jonkd.
        """
        print("Please input expected program runtime:")
        
        while True:
            try:
                sigma2_n_minutes = raw_input_save("minutes (default 10): ")
                if sigma2_n_minutes == "":
                    sigma2_n_minutes = 10
                sigma2_n_minutes = int(sigma2_n_minutes)
                if (sigma2_n_minutes < 0) or (60 < sigma2_n_minutes):
                    print("Number of minutes must larger than 0 and lower than 61.")
                    continue
                break
            
            except ValueError:
                continue

        while True:
            try:
                sigma2_n_hours = raw_input_save("hours (default 0): ")
                if sigma2_n_hours == "":
                    sigma2_n_hours = 0
                sigma2_n_hours = int(sigma2_n_hours)
                if (sigma2_n_hours < 0) or (24 < sigma2_n_hours):
                    print("Number of hours must be 0 or larger, and lower than 24.")
                    continue
                break

            except ValueError:
                continue

        while True:
            try:
                sigma2_n_days = raw_input_save("days (default 0): ")
                if sigma2_n_days == "":
                    sigma2_n_days = 0
                sigma2_n_days = int(sigma2_n_days)
                if (sigma2_n_days < 0):
                    print("Number of days must be 0 or larger.")
                    continue
                break

            except ValueError:
                continue

        sigma2_project_name = raw_input_save("project name (default NN9464K): ")
        sigma2_user_email = raw_input_save("email (default jonkd@uio.no): ")

        # Set default values if no input is given.
        if sigma2_project_name == "":
            sigma2_project_name = "NN9464K"
        if sigma2_user_email == "":
            sigma2_user_email = "jonkd@uio.no"

        if mpi_input_ans.split(",")[0] == "fram":
            while True:
                type_of_fram_job = raw_input_save("type of job (default 'normal'): ")
                
                if type_of_fram_job == "":
                    type_of_fram_job = "normal"

                if type_of_fram_job not in type_of_fram_jobs_list:
                    print("Allowed job types are: ", type_of_fram_jobs_list)
                    continue
                
                else:
                    print(fram_job_description[type_of_fram_job])
                    break

        elif mpi_input_ans.split(",")[0] == "betzy":
            while True:
                type_of_betzy_job = raw_input_save("type of job (default 'normal'): ")
                
                if type_of_betzy_job == "":
                    type_of_betzy_job = "normal"

                if type_of_betzy_job not in type_of_betzy_jobs_list:
                    print("Allowed job types are: ", type_of_betzy_jobs_list)
                    continue
                
                else:
                    print(betzy_job_description[type_of_betzy_job])
                    break

        if len(mpi_input_arr) == 1:
            while True:
                try:
                    msg = f"number of nodes (default {n_nodes}): "
                    n_nodes_input = raw_input_save(msg)
                    
                    if n_nodes_input == "":
                        """
                        Keep n_nodes default value.
                        """
                        break
                    
                    n_nodes_input = int(n_nodes_input)
                    if n_nodes_input < 0:
                        print("The number of nodes must be greater than 0")
                        continue
                    
                    n_nodes = n_nodes_input
                    break

                except ValueError:
                    print("Please enter an integer.")
                    continue
            
        if (mpi_input_ans.split(",")[0] == "fram") or (mpi_input_ans.split(",")[0] == "betzy"):
            while True:
                try:
                    msg = f"number of tasks per node (MPI ranks per node) (default {n_tasks_per_node}): "
                    n_tasks_per_node_input = raw_input_save(msg)
                    
                    if n_tasks_per_node_input == "":
                        """
                        Keep n_tasks_per_node default value.
                        """
                        break
                    
                    n_tasks_per_node_input = int(n_tasks_per_node_input)
                    if n_tasks_per_node_input < 0:
                        msg = "The number of tasks per node must be greater than 0"
                        print(msg)
                        continue
                    
                    n_tasks_per_node = n_tasks_per_node_input
                    break

                except ValueError:
                    print("Please enter an integer.")
                    continue

            while True:
                try:
                    msg = f"number of cpus per task (OpenMP threads per MPI rank) (default {n_cpus_per_task}): "
                    n_cpus_per_task_input = raw_input_save(msg)
                    
                    if n_cpus_per_task_input == "":
                        """
                        Keep n_cpus_per_task default value.
                        """
                        break
                    
                    n_cpus_per_task_input = int(n_cpus_per_task_input)
                    if n_cpus_per_task_input < 0:
                        msg = "The number of cpus per task must be greater than 0"
                        print(msg)
                        continue
                    
                    n_cpus_per_task = n_cpus_per_task_input
                    break

                except ValueError:
                    print("Please enter an integer.")
                    continue
            
            msg = "Double OMP_NUM_THREADS to force SMT? "
            print(msg)
            help_msg = "This option is applicable to Betzy where Slurm only lets us use the physical cores. "
            help_msg += "Setting OMP_NUM_THREADS after the Slurm commands, tricks the system into letting us use as many OpenMP threads as we want, "
            help_msg += "and by doubling it we enable usage of all virtual cores."
            double_omp_yes_inputs = ["y", "yes", ""]
            double_omp_no_inputs = ["n", "no", ""]
            omp_num_threads = None
            while True:
                msg = "Double? (default 'yes', 'help' for info): "
                double_omp_threads_input = raw_input_save(msg)
                double_omp_threads_input = double_omp_threads_input.lower()

                if double_omp_threads_input in double_omp_yes_inputs:
                    omp_num_threads = int(n_cpus_per_task*2)
                    break
                elif double_omp_threads_input in double_omp_no_inputs:
                    break
                elif double_omp_threads_input == "help":
                    print(help_msg)
                    continue
                else:
                    continue

    if len(mpi_input_arr) >= 2:
        """
        Number of nodes may be given as the second argument in the MPI
        input.
        """
        n_nodes = int(mpi_input_arr[1])
    mpi_input_ans = mpi_input_arr[0]
    
    readline.parse_and_bind("tab: None")

    if mpi_input_ans[0].lower() == 'y':
        is_mpi = True
    elif mpi_input_ans[0].lower() == 'n':
        is_mpi = False
    else: 
        is_mpi = mpi_input_ans

    if is_mpi == 'oakforest-pacs': is_mpi = 'ofp'

    txt = '  ... generate shell script for MPI run on '
    if is_mpi == 'coma': 
        print(txt + 'COMA/Tsukuba with SLURM')
    elif is_mpi == 'k' or is_mpi == 'k-micro': 
        print(txt + 'on K-computer micro with PJM')
    elif is_mpi == 'k-small': 
        print(txt + 'on K-computer small with PJM and staging')
    elif is_mpi == 'k-large': 
        print(txt + 'on K-computer large with PJM and staging')
    elif is_mpi == 'ofp':
        print(txt + 'on oakforest-pacs')
    elif is_mpi == 'ofp-flat':
        print(txt + 'on oakforest-pacs flat mode')
    elif is_mpi == 'fram': 
        print(txt + "on Fram@UiT with SLURM ")
    elif is_mpi == 'betzy': 
        print(txt + "on Betzy@NTNU with SLURM ")
    elif is_mpi: 
        print(txt + 'K-computer/FX10 with PJM. ')
    else: 
        print('  ... generate shell script for a single node.')

    list_snt = os.listdir( bindir + "/../snt/" ) \
        + [ fn for fn in os.listdir(".") 
            if (len(fn) > 4) and (fn[-4:] == ".snt") ]
    
    readline.parse_and_bind("tab: complete")
    readline.set_completer( SimpleCompleter(list_snt).complete )
    
    while True:
        """
        Fetch model space (.snt) input from user.
        """
        model_space_msg = "\n model space and interaction file name (.snt) \n"
        model_space_msg += " (e.g. w or w.snt,  TAB to complete) : "
        model_space_filename = raw_input_save(model_space_msg)
        model_space_filename = model_space_filename.rstrip()
        
        if model_space_filename[-4:] != '.snt': model_space_filename = model_space_filename + '.snt'
        if os.path.isfile(model_space_filename):
            """
            Check if model space is defined.
            """
            break
        elif os.path.isfile(bindir + "/../snt/" + model_space_filename):
            """
            Check if model space is defined.
            """
            shutil.copy(bindir + "/../snt/" + model_space_filename, ".")
            break
        
        print("\n *** Invalid: .snt file NOT found  ***")
        
    readline.parse_and_bind("tab: None")
    stgin_filenames.append(model_space_filename)
    read_snt(model_space_filename)

    var_dict[ 'fn_int' ] =  '"' + model_space_filename + '"'
    if (var_dict[ 'beta_cm' ] == 0.0) and check_cm_snt(model_space_filename): 
        var_dict[ 'beta_cm' ] = 10.0
    if is_mpi: var_dict['mode_lv_hdd'] = 0
    if snt_parameters['ncore'] == (8,8): var_dict['hw_type'] = 2

    shell_filename = ''
    fn_snt_base = model_space_filename[:-4]
    shell_file_content_total = ''

    """
    list_jpn:
        A list containing tuples with the 2*spin, parity, number of
        states, and is_jproj for each requested state to be calculated.
    """

    states = []
    while True:
        """
        Fetch nuclide information from user.
        """
        base_filename, shell_file_content_single, valence_p_n, list_jpn, fn_save_dict = \
            main_nuclide(model_space_filename)
        
        if not shell_file_content_single:
            """
            No new nuclide information specified.
            """
            break
        
        for spin, parity, n_states, is_jproj  in list_jpn:
            states.append((
                valence_p_n,
                spin,
                parity,
                n_states,
                is_jproj,
                base_filename,
                fn_save_dict[(spin, parity, n_states, is_jproj)]
            ))
        
        shell_file_content_total += shell_file_content_single
        
        if shell_filename: 
            if len(shell_filename) > len(fn_snt_base) \
               and shell_filename[-len(fn_snt_base):] == fn_snt_base:
                shell_filename = shell_filename[:-len(fn_snt_base)]
            else:
                shell_filename += '_'
        
        shell_filename += base_filename

    if not shell_filename:
        """
        End program if no nuclide is specified.
        """
        print("\n*** NO input ***\n")
        return

    gt_pair = [ ( (nf1, m1, p1, n1, isj1, fn_base1, fn_wp1),  
                  (nf2, m2, p2, n2, isj2, fn_base2, fn_wp2) )
                for (nf1, m1, p1, n1, isj1, fn_base1, fn_wp1) in states
                for (nf2, m2, p2, n2, isj2, fn_base2, fn_wp2) in states
                if nf1[0] == nf2[0] + 1 and sum(nf1)==sum(nf2) 
                and p1 == p2 and abs(m1-m2)<=2 ]

    sfac_pair = [ ( (nf1, m1, p1, n1, isj1, fn_base1, fn_wp1),  
                    (nf2, m2, p2, n2, isj2, fn_base2, fn_wp2) )
                  for (nf1, m1, p1, n1, isj1, fn_base1, fn_wp1) in states
                  for (nf2, m2, p2, n2, isj2, fn_base2, fn_wp2) in states
                  if (nf1[0] == nf2[0]+1 and nf1[1] == nf2[1])
                  or (nf1[0] == nf2[0]   and nf1[1] == nf2[1]+1) ]

    def output_transit_pair(pair):
        shell_file_content_total = ''
        for (nf1, m1, p1, n1, isj1, fn_base1, fn_wp1), \
            (nf2, m2, p2, n2, isj2, fn_base2, fn_wp2) in pair: 
            base_filename = fn_base1
            if len(base_filename)> len(fn_snt_base) \
               and base_filename[-len(fn_snt_base):] == fn_snt_base:
                base_filename = base_filename[:-len(fn_snt_base)]
            else:
                base_filename += '_'
            base_filename += fn_base2

            input_filename = base_filename + '_' + str(m1) + '_' + str(m2) + '.input'

            shell_file_content_total += output_transit(
                base_filename, input_filename, fn_wp1, fn_wp2, (m1, p1, n1, isj1),
                (m2, p2, n2, isj2)
            )
        return shell_file_content_total


    if gt_pair and ask_yn('Gamow-teller transition'):
        shell_file_content_total += '# ------ Gamow Teller transition ------ \n'
        shell_file_content_total += 'echo \n'
        shell_file_content_total += 'echo "Gamow Teller transition calc."\n'
        shell_file_content_total += output_transit_pair(gt_pair)

    if sfac_pair and ask_yn('one-particle spectroscopic factor'):
        shell_file_content_total += '# --------- spectroscocpic factor --------- \n'
        shell_file_content_total += 'echo \n'
        shell_file_content_total += 'echo "spectroscopic factor calc."\n'
        shell_file_content_total += output_transit_pair(sfac_pair)

    shell_filename += ".sh"

    def check_copy(*fnames):
        """
        Copy needed files (typically 'kshell.exe', 'transit.exe',
        'collect_logs.py') from <kshell_install_dir/bin> to the run
        directory (the directory where this file is called from).

        Print a warning message if the files do not exist and cannot be
        copied. This happens if the source files are not yet compiled.
        Program does not terminate by this warning.

        Parameters
        ----------
        *fnames : strings
            Names of files to be copied. Input filenames are gathered
            into a tuple. Input must be individual strings of filenames.
        """
        for fname in fnames:
            binfname = bindir + '/' + fname
            if not os.path.exists( binfname ):
                print("\n*** WARNING: NOT found " + bindir + '/' + fname, " ***")
            else:
                try:
                    shutil.copy( binfname, '.' )
                except IOError:
                    print( "\n*** WARNING: copy " + binfname \
                        + " to current dir. failed ***")
    
    # header
    if is_mpi:
        check_copy('kshell.exe', 'transit.exe', 'collect_logs.py', 'count_dim.py') 
        if is_mpi == 'coma':
            shell_file_content_total = '#!/bin/sh \n' \
                    + '#SBATCH -J ' + shell_filename[:-3] + '\n' \
                    + '#SBATCH -p mixed\n' \
                    + '#SBATCH -N ' + str(n_nodes) + '\n' \
                    + '#SBATCH -n ' + str(n_nodes) + '\n' \
                    + '# #SBATCH -t 01:00:00\n' \
                    + '#SBATCH --cpus-per-task=20\n' \
                    + '#SBATCH -o stdout\n' \
                    + '#SBATCH -e stderr\n\n' \
                    + 'export OMP_NUM_THREADS=20\n\n' \
                    + 'module load mkl intel intelmpi \n' \
                    + shell_file_content_total 
                    # + 'cd ' + os.getcwd() +'\n\n' \
                    # cd $SLURM_SUBMIT_DIR
                    # export OMP_NUM_THREADS=16
            
            print("\n Finish. edit and sbatch ./"+shell_filename+"\n")
        elif is_mpi == 'k' or is_mpi == 'k-micro': 
            shell_file_content_total = '#!/bin/sh \n' \
                    + '#PJM -L "rscgrp=micro"\n' \
                    + '#PJM -L "node=' + str(n_nodes) + '"\n' \
                    + '#PJM -L "elapse=00:30:00"\n' \
                    + '#PJM -g "XXXXXXXX"\n\n' \
                    + '. /work/system/Env_base\n\n' \
                    + shell_file_content_total 
                    # + 'cd ' + os.getcwd() +'\n\n' \
        elif is_mpi == 'k-small': 
            outstg = '#PJM --stgin "'
            for fn in stgin_filenames: outstg += './'+fn+' '
            outstg += './"\n'
            outstg += '#PJM --stgout "'
            for fn in stgout_filenames: outstg += './'+fn+' '
            outstg += './"\n\n'
            shell_file_content_total = '#!/bin/sh \n' \
                    + '#PJM -L "rscgrp=small"\n' \
                    + '#PJM -L "node=' + str(n_nodes) + '"\n' \
                    + '#PJM -L "elapse=00:30:00"\n' \
                    + outstg \
                    + '. /work/system/Env_base\n\n' \
                    + 'lfs setstripe -s 100m -c 12 .\n\n' \
                    + shell_file_content_total 
        elif is_mpi == 'k-large': 
            outstg = '#PJM --stgin "'
            for fn in stgin_filenames: outstg += './'+fn+' '
            outstg += './"\n'
            outstg += '#PJM --stgout "'
            for fn in stgout_filenames: outstg += './'+fn+' '
            outstg += './"\n\n'
            shell_file_content_total = '#!/bin/sh \n' \
                    + '#PJM -L "rscgrp=large"\n' \
                    + '#PJM -L "node=' + str(n_nodes) + '"\n' \
                    + '#PJM -L "elapse=06:00:00"\n' \
                    + outstg \
                    + '. /work/system/Env_base\n\n' \
                    + 'lfs setstripe -s 100m -c 12 .\n\n' \
                    + shell_file_content_total 
        elif is_mpi == 'ofp': 
            shell_file_content_total = '#!/bin/sh \n' \
                    + '#PJM -L "rscgrp=debug-cache"\n' \
                    + '#PJM -L "node=' + str(n_nodes) + '"\n' \
                    + '#PJM --omp thread=272\n' \
                    + '#PJM -L "elapse=00:30:00"\n' \
                    + '#PJM -g XXXXXXXX\n' \
                    + shell_file_content_total 
        elif is_mpi == 'ofp-flat': 
            shell_file_content_total = '#!/bin/sh \n' \
                    + '#PJM -L "rscgrp=debug-flat"\n' \
                    + '#PJM -L "node=' + str(n_nodes) + '"\n' \
                    + '# #PJM --mpi "proc=' + str(n_nodes) + '"\n' \
                    + '#PJM --omp thread=272\n' \
                    + '#PJM -L "elapse=00:30:00"\n' \
                    + '#PJM -g XXXXXX\n' \
                    + shell_file_content_total 
        elif is_mpi == 'cx400': 
            shell_file_content_total = \
            '''#!/bin/sh 
            #PJM -L "rscgrp=XXXXXXXX"
            #PJM -L "vnode=''' + str(n_nodes) + '''"
            #PJM -L "vnode-core=28"
            # #PJM --mpi "rank-map-bynode"
            #PJM -P "vn-policy=abs-unpack"
            #PJM -L "elapse=01:00:00"
            #

            source /center/local/apl/cx/intel/composerxe/bin/compilervars.sh intel64
            source /center/local/apl/cx/intel/impi/4.1.1.036/bin64/mpivars.sh
            source /center/local/apl/cx/intel/mkl/bin/mklvars.sh intel64

            export I_MPI_PIN_DOMAIN=omp
            # export OMP_NUM_THREADS=28
            export I_MPI_HYDRA_BOOTSTRAP=rsh
            export I_MPI_HYDRA_BOOTSTRAP_EXEC=/bin/pjrsh
            export I_MPI_HYDRA_HOST_FILE=${PJM_O_NODEINF}
            export FORT90L=-Wl,-Lu
            '''  + shell_file_content_total
                    # + 'cd ' + os.getcwd() +'\n\n' \
            print("\n Finish. edit and pjsub ./" + shell_filename + "\n")

        elif is_mpi == 'fram': # This option is added by JEM / jonkd.
            shell_file_content_tmp = '#!/bin/bash \n'
            shell_file_content_tmp += f'#SBATCH --job-name={shell_filename[:-3]} \n'
            shell_file_content_tmp += f'#SBATCH --account={sigma2_project_name} \n'
            shell_file_content_tmp += '## Syntax is d-hh:mm:ss \n'
            shell_file_content_tmp += f'#SBATCH --time={sigma2_n_days}-{sigma2_n_hours:02d}:{sigma2_n_minutes:02d}:00 \n'
            shell_file_content_tmp += f'#SBATCH --nodes={n_nodes}\n'
            shell_file_content_tmp += f'#SBATCH --ntasks-per-node={n_tasks_per_node} \n'
            shell_file_content_tmp += f'#SBATCH --cpus-per-task={n_cpus_per_task} \n'
            shell_file_content_tmp += '#SBATCH --mail-type=ALL \n'
            shell_file_content_tmp += f'#SBATCH --mail-user={sigma2_user_email} \n'
            if type_of_fram_job != "normal":
                shell_file_content_tmp += f'#SBATCH --qos={type_of_fram_job} \n'
            shell_file_content_tmp += 'module --quiet purge  \n'
            # shell_file_content_tmp += 'module load foss/2017a \n'
            shell_file_content_tmp += 'module load intel/2020b \n'
            shell_file_content_tmp += 'module load Python/3.8.6-GCCcore-10.2.0 \n'
            shell_file_content_tmp += 'set -o errexit  \n'
            shell_file_content_tmp += 'set -o nounset \n'
            shell_file_content_tmp += shell_file_content_total
            shell_file_content_total = shell_file_content_tmp

        elif is_mpi == 'betzy': # This option is added by jonkd.
            shell_file_content_tmp = '#!/bin/bash \n'
            shell_file_content_tmp += f'#SBATCH --job-name={shell_filename[:-3]} \n'
            shell_file_content_tmp += f'#SBATCH --account={sigma2_project_name} \n'
            shell_file_content_tmp += '## Syntax is d-hh:mm:ss \n'
            shell_file_content_tmp += f'#SBATCH --time={sigma2_n_days}-{sigma2_n_hours:02d}:{sigma2_n_minutes:02d}:00 \n'
            shell_file_content_tmp += f'#SBATCH --nodes={n_nodes}\n'
            shell_file_content_tmp += f'#SBATCH --ntasks-per-node={n_tasks_per_node} \n'
            shell_file_content_tmp += f'#SBATCH --cpus-per-task={n_cpus_per_task} \n'
            shell_file_content_tmp += '#SBATCH --mail-type=ALL \n'
            shell_file_content_tmp += f'#SBATCH --mail-user={sigma2_user_email} \n'
            
            if type_of_betzy_job != "normal":
                shell_file_content_tmp += f'#SBATCH --qos={type_of_betzy_job} \n'
            
            shell_file_content_tmp += 'module --quiet purge  \n'
            shell_file_content_tmp += 'module load intel/2020b \n'
            shell_file_content_tmp += 'module load Python/3.8.6-GCCcore-10.2.0 \n'
            shell_file_content_tmp += 'set -o errexit  \n'
            shell_file_content_tmp += 'set -o nounset \n'
            
            if omp_num_threads is not None:
                shell_file_content_tmp += f'export OMP_NUM_THREADS={omp_num_threads} \n'
            
            shell_file_content_tmp += shell_file_content_total
            shell_file_content_total = shell_file_content_tmp

        else: # FX10
            shell_file_content_total = '#!/bin/sh \n' \
                    + '#PJM -L "rscgrp=debug"\n' \
                    + '#PJM -L "node=' + str(n_nodes) + '"\n' \
                    + '# #PJM -L "elapse=24:00:00"\n\n' \
                    + shell_file_content_total 
                    # + 'cd ' + os.getcwd() +'\n\n' \
            print("\n Finish. edit and pjsub ./" + shell_filename + "\n")
    else:
        check_copy('kshell.exe', 'transit.exe', 'collect_logs.py', 'count_dim.py') 
        shell_file_content_total = '#!/bin/sh \n' \
                + '# export OMP_STACKSIZE=1g\n' \
                + 'export GFORTRAN_UNBUFFERED_PRECONNECTED=y\n' \
                + '# ulimit -s unlimited\n\n' \
                + shell_file_content_total 
        print("\n Finish. Run ./" + shell_filename + "\n")

    fp_save_input = open('save_input_ui.txt', 'w')
    fp_save_input.write( gen_partition.output_ans )
    fp_save_input.close()
    
    shell_file_content_total = \
        check_j_scheme_dimensionality(
            states,
            model_space_filename,
            shell_file_content_total
        )
    
    fp_run = open(shell_filename, 'w')
    fp_run.write(shell_file_content_total)
    fp_run.close()

    if not is_mpi: os.chmod(shell_filename, 0o755)
 
if __name__ == "__main__":
    main()