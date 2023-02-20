try:
    from kshell.parameters import *
except ImportError:
    msg = """Error importing kshell: you should not try to import kshell from
    its source directory unless it is a submodule; please exit the kshell
    source tree, and relaunch."""
    raise ImportError(msg)

from .version import GIT_REVISION as __git_revision__
from .version import VERSION as __version__
from .version import FULLVERSION as __full_version__

from .parameters import (GS_FREE_PROTON, GS_FREE_NEUTRON,
                         recommended_quenching_factors)
from .gen_partition import raw_input_save

