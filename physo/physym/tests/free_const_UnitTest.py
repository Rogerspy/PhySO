import time
import unittest
import torch
import numpy as np

# Internal imports
import physo.physym.free_const as free_const

# For testing whole opti process : test_optimization_process
from physo.physym import library as Lib
from physo.physym import vect_programs as VProg
from physo.physym.functions import data_conversion, data_conversion_inv
from physo.physym import execute as Exec


class FreeConstUtilsTest(unittest.TestCase):

    # Testing that LBFGS optimizer is working properly with torch
    def test_lgbs_optimizer (self):

        DEVICE = 'cpu'
        if torch.cuda.is_available():
            DEVICE = 'cuda'

        # ------ Test case ------
        # Data
        N = 100
        r = data_conversion(np.linspace(-10, 10, N)).to(DEVICE)
        v = data_conversion(np.linspace(-10, 10, N)).to(DEVICE)
        X = torch.stack((r,v), axis=0)

        func = lambda params, X: params[0] * X[1] ** 2 + (params[1] ** 2) * torch.log(X[0] ** 2 + params[2] ** 2)

        ideal_params = [0.5, 1.14, 0.936]
        func_params = lambda params: func(params, X)
        y_target = func_params(params=ideal_params)

        n_params = len(ideal_params)

        # ------ Run ------
        total_n_steps = 0
        t0 = time.perf_counter()

        N = 100
        for _ in range (N):

            params_init = 1. * torch.ones(n_params, ).to(DEVICE)
            params = params_init

            history = free_const.optimize_free_const (     func     = func_params,
                                                           params   = params,
                                                           y_target = y_target,
                                                           loss        = "MSE",
                                                           method      = "LBFGS",
                                                           method_args = None)
            total_n_steps += history.shape[0]

        t1 = time.perf_counter()
        dt = ((t1-t0)*1e3)/total_n_steps
        print("LBFGS const opti: %f ms / step" %(dt))

        # ------ Test ------
        obs_params   = params.detach().cpu().numpy()
        ideal_params = np.array(ideal_params)
        for i in range (n_params):
            err = np.abs(obs_params[0] - ideal_params[0])
            works_bool = (err < 1e-6)
            self.assertEqual(works_bool, True)

        return None

class FreeConstantsTableTest(unittest.TestCase):


    def test_table_shape (self):

        batch_size = 128

        k0_init = [9,10,11]*10 # np.full(n_realizations, 1.)
        n_realizations = len(k0_init)

        # consts
        pi     = data_conversion (np.pi)
        const1 = data_conversion (1.)

        # -------- Class and spe free constants --------
        # LIBRARY CONFIG
        args_make_tokens = {
                        # operations
                        "op_names"             : "all",
                        "use_protected_ops"    : True,
                        # input variables
                        "input_var_ids"        : {"t" : 0         , "l" : 1          },
                        "input_var_units"      : {"t" : [1, 0, 0] , "l" : [0, 1, 0]  },
                        "input_var_complexity" : {"t" : 0.        , "l" : 1.         },
                        # constants
                        "constants"            : {"pi" : pi        , "const1" : const1    },
                        "constants_units"      : {"pi" : [0, 0, 0] , "const1" : [0, 0, 0] },
                        "constants_complexity" : {"pi" : 1.        , "const1" : 1.        },
                        # free constants
                        "class_free_constants"            : {"c0"              , "c1"               },
                        "class_free_constants_init_val"   : {"c0" : 21.        , "c1"  : 22.         },
                        "class_free_constants_units"      : {"c0" : [-1, 0, 0] , "c1"  : [0, -1, 0] },
                        "class_free_constants_complexity" : {"c0" : 1.         , "c1"  : 1.         },
                        # free constants
                        "spe_free_constants"            : {"k0"              , "k1"               , "k2"               },
                        "spe_free_constants_init_val"   : {"k0" : k0_init    , "k1"  : 2.         , "k2"  : 3.         },
                        "spe_free_constants_units"      : {"k0" : [0, 0, 0]  , "k1"  : [-1, 0, 0] , "k2"  : [0, 0, 0]  },
                        "spe_free_constants_complexity" : {"k0" : 1.         , "k1"  : 1.         , "k2"  : 1.         },
                           }

        my_lib = Lib.Library(args_make_tokens = args_make_tokens,
                             superparent_units = [0, 0, 0], superparent_name = "y")

        table = free_const.FreeConstantsTable(batch_size, my_lib, n_realizations=n_realizations)

        expected_spe_shape   = (batch_size, 3, n_realizations)
        expected_class_shape = (batch_size, 2)

        # Testing that table is of the right shape
        works_bool = (table.spe_values.shape   == expected_spe_shape)
        self.assertEqual(works_bool, True)
        works_bool = (table.class_values.shape == expected_class_shape)
        self.assertEqual(works_bool, True)
        works_bool = (table.shape == (expected_class_shape, expected_spe_shape))
        self.assertEqual(works_bool, True)

        # -------- Without any free constants --------
        # LIBRARY CONFIG
        args_make_tokens = {
                        # operations
                        "op_names"             : "all",
                        "use_protected_ops"    : True,
                        # input variables
                        "input_var_ids"        : {"t" : 0         , "l" : 1          },
                        "input_var_units"      : {"t" : [1, 0, 0] , "l" : [0, 1, 0]  },
                        "input_var_complexity" : {"t" : 0.        , "l" : 1.         },
                        # constants
                        "constants"            : {"pi" : pi        , "const1" : const1    },
                        "constants_units"      : {"pi" : [0, 0, 0] , "const1" : [0, 0, 0] },
                        "constants_complexity" : {"pi" : 1.        , "const1" : 1.        },
                           }
        my_lib = Lib.Library(args_make_tokens = args_make_tokens,
                             superparent_units = [0, 0, 0], superparent_name = "y")

        table = free_const.FreeConstantsTable(batch_size, my_lib, n_realizations=n_realizations)

        expected_spe_shape   = (batch_size, 0, n_realizations)
        expected_class_shape = (batch_size, 0)

        # Testing that table is of the right shape
        works_bool = (table.spe_values.shape   == expected_spe_shape)
        self.assertEqual(works_bool, True)
        works_bool = (table.class_values.shape == expected_class_shape)
        self.assertEqual(works_bool, True)
        works_bool = (table.shape == (expected_class_shape, expected_spe_shape))
        self.assertEqual(works_bool, True)

        # -------- Without class free constants --------
        # LIBRARY CONFIG
        args_make_tokens = {
                        # operations
                        "op_names"             : "all",
                        "use_protected_ops"    : True,
                        # input variables
                        "input_var_ids"        : {"t" : 0         , "l" : 1          },
                        "input_var_units"      : {"t" : [1, 0, 0] , "l" : [0, 1, 0]  },
                        "input_var_complexity" : {"t" : 0.        , "l" : 1.         },
                        # constants
                        "constants"            : {"pi" : pi        , "const1" : const1    },
                        "constants_units"      : {"pi" : [0, 0, 0] , "const1" : [0, 0, 0] },
                        "constants_complexity" : {"pi" : 1.        , "const1" : 1.        },
                        # free constants
                        "spe_free_constants"            : {"k0"              , "k1"               , "k2"               },
                        "spe_free_constants_init_val"   : {"k0" : k0_init    , "k1"  : 2.         , "k2"  : 3.         },
                        "spe_free_constants_units"      : {"k0" : [0, 0, 0]  , "k1"  : [-1, 0, 0] , "k2"  : [0, 0, 0]  },
                        "spe_free_constants_complexity" : {"k0" : 1.         , "k1"  : 1.         , "k2"  : 1.         },
                           }
        my_lib = Lib.Library(args_make_tokens = args_make_tokens,
                             superparent_units = [0, 0, 0], superparent_name = "y")

        table = free_const.FreeConstantsTable(batch_size, my_lib, n_realizations=n_realizations)

        expected_spe_shape   = (batch_size, 3, n_realizations)
        expected_class_shape = (batch_size, 0)

        # Testing that table is of the right shape
        works_bool = (table.spe_values.shape   == expected_spe_shape)
        self.assertEqual(works_bool, True)
        works_bool = (table.class_values.shape == expected_class_shape)
        self.assertEqual(works_bool, True)
        works_bool = (table.shape == (expected_class_shape, expected_spe_shape))
        self.assertEqual(works_bool, True)

        # -------- Without spe free constants --------
        # LIBRARY CONFIG
        args_make_tokens = {
                        # operations
                        "op_names"             : "all",
                        "use_protected_ops"    : True,
                        # input variables
                        "input_var_ids"        : {"t" : 0         , "l" : 1          },
                        "input_var_units"      : {"t" : [1, 0, 0] , "l" : [0, 1, 0]  },
                        "input_var_complexity" : {"t" : 0.        , "l" : 1.         },
                        # constants
                        "constants"            : {"pi" : pi        , "const1" : const1    },
                        "constants_units"      : {"pi" : [0, 0, 0] , "const1" : [0, 0, 0] },
                        "constants_complexity" : {"pi" : 1.        , "const1" : 1.        },
                        # free constants
                        "class_free_constants"            : {"c0"              , "c1"               },
                        "class_free_constants_init_val"   : {"c0" : 21.        , "c1"  : 22.         },
                        "class_free_constants_units"      : {"c0" : [-1, 0, 0] , "c1"  : [0, -1, 0] },
                        "class_free_constants_complexity" : {"c0" : 1.         , "c1"  : 1.         },
                           }
        my_lib = Lib.Library(args_make_tokens = args_make_tokens,
                             superparent_units = [0, 0, 0], superparent_name = "y")


        table = free_const.FreeConstantsTable(batch_size, my_lib, n_realizations=n_realizations)

        expected_spe_shape   = (batch_size, 0, n_realizations)
        expected_class_shape = (batch_size, 2)

        # Testing that table is of the right shape
        works_bool = (table.spe_values.shape   == expected_spe_shape)
        self.assertEqual(works_bool, True)
        works_bool = (table.class_values.shape == expected_class_shape)
        self.assertEqual(works_bool, True)
        works_bool = (table.shape == (expected_class_shape, expected_spe_shape))
        self.assertEqual(works_bool, True)

    # Testing reference behavior when exporting single prog consts
    def test_reference_behavior (self):

        k0_init = [9,10,11,12,13] # np.full(n_realizations, 1.)
        n_realizations = len(k0_init)
        # consts
        pi     = data_conversion (np.pi)
        const1 = data_conversion (1.)

        # LIBRARY CONFIG
        args_make_tokens = {
                        # operations
                        "op_names"             : "all",
                        "use_protected_ops"    : True,
                        # input variables
                        "input_var_ids"        : {"t" : 0         , "l" : 1          },
                        "input_var_units"      : {"t" : [1, 0, 0] , "l" : [0, 1, 0]  },
                        "input_var_complexity" : {"t" : 0.        , "l" : 1.         },
                        # constants
                        "constants"            : {"pi" : pi        , "const1" : const1    },
                        "constants_units"      : {"pi" : [0, 0, 0] , "const1" : [0, 0, 0] },
                        "constants_complexity" : {"pi" : 1.        , "const1" : 1.        },
                        # free constants
                        "class_free_constants"            : {"c0"              , "c1"                },
                        "class_free_constants_init_val"   : {"c0" : 1.1        , "c1"  : 2.2         },
                        "class_free_constants_units"      : {"c0" : [-1, 0, 0] , "c1"  : [0, -1, 0]  },
                        "class_free_constants_complexity" : {"c0" : 1.         , "c1"  : 1.          },
                        # free constants
                        "spe_free_constants"            : {"k0"              , "k1"               , "k2"               },
                        "spe_free_constants_init_val"   : {"k0" : k0_init    , "k1"  : 2.         , "k2"  : 3.         },
                        "spe_free_constants_units"      : {"k0" : [0, 0, 0]  , "k1"  : [-1, 0, 0] , "k2"  : [0, 0, 0]  },
                        "spe_free_constants_complexity" : {"k0" : 1.         , "k1"  : 1.         , "k2"  : 1.         },
                           }
        my_lib = Lib.Library(args_make_tokens = args_make_tokens,
                             superparent_units = [0, 0, 0], superparent_name = "y")

        n_class_free_consts = 2
        n_spe_free_consts   = 3
        batch_size = 128
        table = free_const.FreeConstantsTable(batch_size, my_lib, n_realizations=n_realizations)

        # fake ideal constants (let's make them different for each prog in batch and for each realization)
        ideal_c0 = np.arange(batch_size)+0.1     # (batch_size,)
        ideal_c1 = np.arange(batch_size)+0.2     # (batch_size,)
        ideal_class_values = np.stack([ideal_c0, ideal_c1], axis=1) # (batch_size, n_class_free_consts)
        ideal_class_values = torch.tensor(ideal_class_values)
        ideal_k0 = np.add.outer(np.arange(batch_size) + 0.3, 0.01*np.arange(n_realizations))  # (batch_size, n_realizations,)
        ideal_k1 = np.add.outer(np.arange(batch_size) + 0.4, 0.01*np.arange(n_realizations))  # (batch_size, n_realizations,)
        ideal_k2 = np.add.outer(np.arange(batch_size) + 0.5, 0.01*np.arange(n_realizations))  # (batch_size, n_realizations,)
        ideal_spe_values = np.stack([ideal_k0, ideal_k1, ideal_k2], axis=1) # (batch_size, n_spe_free_consts, n_realizations)
        ideal_spe_values = torch.tensor(ideal_spe_values)
        new_is_opti    = np.arange(batch_size) % 2 == 0 # (batch_size,)
        new_opti_steps = np.arange(batch_size) + 1000   # (batch_size,)

        for i_prog in range (batch_size):

            prog_table = table.get_const_of_prog(i_prog)            # (1, n_class_free_consts), (1, n_spe_free_consts, n_realizations)
            prog_table.class_values[0] = ideal_class_values [i_prog] # (n_class_free_consts,)
            prog_table.spe_values  [0] = ideal_spe_values   [i_prog] # (n_spe_free_consts, n_realizations)
            prog_table.is_opti     [0] = new_is_opti     [i_prog] # (1,)
            prog_table.opti_steps  [0] = new_opti_steps  [i_prog] # (1,)


        # Testing that table is modified by reference when modifying prog_table
        works_bool = (table.class_values == ideal_class_values).all()
        self.assertEqual(works_bool, True)
        works_bool = (table.spe_values == ideal_spe_values).all()
        self.assertEqual(works_bool, True)
        works_bool = (table.is_opti == new_is_opti).all()
        self.assertEqual(works_bool, True)
        works_bool = (table.opti_steps == new_opti_steps).all()
        self.assertEqual(works_bool, True)

        return None


    # Testing that affecting a single prog's consts does not affect the general table when they are detached
    def test_detach_behavior (self):

        k0_init = [9,10,11,12,13] # np.full(n_realizations, 1.)
        n_realizations = len(k0_init)
        # consts
        pi     = data_conversion (np.pi)
        const1 = data_conversion (1.)

        # LIBRARY CONFIG
        args_make_tokens = {
                        # operations
                        "op_names"             : "all",
                        "use_protected_ops"    : True,
                        # input variables
                        "input_var_ids"        : {"t" : 0         , "l" : 1          },
                        "input_var_units"      : {"t" : [1, 0, 0] , "l" : [0, 1, 0]  },
                        "input_var_complexity" : {"t" : 0.        , "l" : 1.         },
                        # constants
                        "constants"            : {"pi" : pi        , "const1" : const1    },
                        "constants_units"      : {"pi" : [0, 0, 0] , "const1" : [0, 0, 0] },
                        "constants_complexity" : {"pi" : 1.        , "const1" : 1.        },
                        # free constants
                        "class_free_constants"            : {"c0"              , "c1"                },
                        "class_free_constants_init_val"   : {"c0" : 1.1        , "c1"  : 2.2         },
                        "class_free_constants_units"      : {"c0" : [-1, 0, 0] , "c1"  : [0, -1, 0]  },
                        "class_free_constants_complexity" : {"c0" : 1.         , "c1"  : 1.          },
                        # free constants
                        "spe_free_constants"            : {"k0"              , "k1"               , "k2"               },
                        "spe_free_constants_init_val"   : {"k0" : k0_init    , "k1"  : 2.         , "k2"  : 3.         },
                        "spe_free_constants_units"      : {"k0" : [0, 0, 0]  , "k1"  : [-1, 0, 0] , "k2"  : [0, 0, 0]  },
                        "spe_free_constants_complexity" : {"k0" : 1.         , "k1"  : 1.         , "k2"  : 1.         },
                           }
        my_lib = Lib.Library(args_make_tokens = args_make_tokens,
                             superparent_units = [0, 0, 0], superparent_name = "y")

        n_class_free_consts = 2
        n_spe_free_consts   = 3
        batch_size = 128
        table = free_const.FreeConstantsTable(batch_size, my_lib, n_realizations=n_realizations)

        # Saving original table
        original_class_values = table.class_values.clone()
        original_spe_values   = table.spe_values  .clone()
        original_is_opti      = table.is_opti     .copy()
        original_opti_steps   = table.opti_steps  .copy()

        # fake ideal constants (let's make them different for each prog in batch and for each realization)
        new_c0 = np.arange(batch_size)+0.1     # (batch_size,)
        new_c1 = np.arange(batch_size)+0.2     # (batch_size,)
        new_class_values = np.stack([new_c0, new_c1], axis=1) # (batch_size, n_class_free_consts)
        new_class_values = torch.tensor(new_class_values)
        new_k0 = np.add.outer(np.arange(batch_size) + 0.3, 0.01*np.arange(n_realizations))  # (batch_size, n_realizations,)
        new_k1 = np.add.outer(np.arange(batch_size) + 0.4, 0.01*np.arange(n_realizations))  # (batch_size, n_realizations,)
        new_k2 = np.add.outer(np.arange(batch_size) + 0.5, 0.01*np.arange(n_realizations))  # (batch_size, n_realizations,)
        new_spe_values = np.stack([new_k0, new_k1, new_k2], axis=1) # (batch_size, n_spe_free_consts, n_realizations)
        new_spe_values = torch.tensor(new_spe_values)
        new_is_opti    = np.arange(batch_size) % 2 == 0 # (batch_size,)
        new_opti_steps = np.arange(batch_size) + 1000   # (batch_size,)

        for i_prog in range (batch_size):

            prog_table = table.get_const_of_prog(i_prog)            # (1, n_class_free_consts), (1, n_spe_free_consts, n_realizations)
            prog_table.detach()
            prog_table.class_values[0] = new_class_values[i_prog] # (n_class_free_consts,)
            prog_table.spe_values  [0] = new_spe_values  [i_prog] # (n_spe_free_consts, n_realizations)
            prog_table.is_opti     [0] = new_is_opti     [i_prog] # (1,)
            prog_table.opti_steps  [0] = new_opti_steps  [i_prog] # (1,)


        # Testing that table is modified by reference when modifying prog_table
        works_bool = (table.class_values == original_class_values).all()
        self.assertEqual(works_bool, True)
        works_bool = (table.spe_values == original_spe_values).all()
        self.assertEqual(works_bool, True)
        works_bool = (table.is_opti == original_is_opti).all()
        self.assertEqual(works_bool, True)
        works_bool = (table.opti_steps == original_opti_steps).all()
        self.assertEqual(works_bool, True)

        return None

    def test_optimization_process (self):

        DEVICE = 'cpu'
        if torch.cuda.is_available():
            DEVICE = 'cuda'

        # Data
        N = 100
        r = data_conversion(np.linspace(-10, 10, N)).to(DEVICE)
        v = data_conversion(np.linspace(-10, 10, N)).to(DEVICE)
        X = torch.stack((r,v), axis=0)

        # consts
        pi     = data_conversion (np.pi) .to(DEVICE)
        const1 = data_conversion (1.)    .to(DEVICE)

        # free consts
        c0_init = 1.
        vc_init = 1.02
        rc_init = 1.03

        # LIBRARY CONFIG
        args_make_tokens = {
                        # operations
                        "op_names"             : "all",
                        "use_protected_ops"    : True,
                        # input variables
                        "input_var_ids"        : {"r" : 0         , "v" : 1          },
                        "input_var_units"      : {"r" : [1, 0, 0] , "v" : [1, -1, 0] },
                        "input_var_complexity" : {"r" : 0.        , "v" : 1.         },
                        # constants
                        "constants"            : {"pi" : pi        , "const1" : const1    },
                        "constants_units"      : {"pi" : [0, 0, 0] , "const1" : [0, 0, 0] },
                        "constants_complexity" : {"pi" : 1.        , "const1" : 1.        },
                        # free constants
                        "free_constants"            : {"c0"             , "vc"               , "rc"             },
                        "free_constants_init_val"   : {"c0" : c0_init   , "vc"  : vc_init    , "rc" : rc_init   },
                        "free_constants_units"      : {"c0" : [0, 0, 0] , "vc"  : [1, -1, 0] , "rc" : [1, 0, 0] },
                        "free_constants_complexity" : {"c0" : 1.        , "vc"  : 1.         , "rc" : 1.        },
                           }
        my_lib = Lib.Library(args_make_tokens = args_make_tokens,
                             superparent_units = [2, -2, 0], superparent_name = "E")

        # TEST PROGRAMS
        test_programs_idx = []
        test_prog_str_0 = ["add", "mul", "mul", "const1", "c0" , "n2", "v", "mul", "n2", "vc", "log", "div", "n2", "r", "n2", "rc"]
        test_prog_str_1 = ["mul", "n2" , "vc" , "cos"   , "div", "r" , "rc", "-", "-", "-", "-", "-", "-", "-", "-", "-"]
        test_programs_str = np.array([test_prog_str_0, test_prog_str_1])

        # Using terminal token placeholder that will be replaced by '-' void token in append function
        test_programs_str = np.char.replace(test_programs_str, '-', 'r')

        # Converting into idx
        for test_program_str in test_programs_str :
            test_programs_idx.append(np.array([my_lib.lib_name_to_idx[tok_str] for tok_str in test_program_str]))
        test_programs_idx = np.array(test_programs_idx)

        # Initializing programs
        my_programs = Prog.VectPrograms(batch_size=test_programs_idx.shape[0], max_time_step=test_programs_idx.shape[1], library=my_lib)

        # Sending free constants to device
        my_programs.free_consts.values = my_programs.free_consts.values.to(DEVICE)

        # Appending tokens
        for i in range (test_programs_idx.shape[1]):
            my_programs.assign_required_units() # useless here: just here for the pleasure of seeing it work properly
            my_programs.append(test_programs_idx[:,i])

        # PROGRAMS
        prog0 = my_programs.get_prog(0)
        prog1 = my_programs.get_prog(1)

        # IDEAL CONSTANTS
        ideal_const_array0 = np.array([0.5, 1.14, 0.936])
        ideal_const0 = data_conversion(ideal_const_array0).to(DEVICE)
        ideal_const_array1 = np.array([0.5, 1.14, 0.936])
        ideal_const1 = data_conversion(ideal_const_array1).to(DEVICE)

        # MAKING SYNTHETIC y_target from ideal constants
        y_target0 = Exec.ExecuteProgram(input_var_data = X, free_const_values = ideal_const0, program_tokens = prog0.tokens, )
        y_target1 = Exec.ExecuteProgram(input_var_data = X, free_const_values = ideal_const1, program_tokens = prog1.tokens, )

        # MSE before optimizing constants
        MSE_before_opti_0 = data_conversion_inv(torch.mean((prog0(X) - y_target0) ** 2))
        MSE_before_opti_1 = data_conversion_inv(torch.mean((prog1(X) - y_target1) ** 2))

        # Optimizing free constants of prog 0
        prog0.optimize_constants(X=X, y_target=y_target0)

        # Testing that opti processed was logged in Program
        works_bool = (prog0.is_opti[0] == True) and (prog1.is_opti[0] == False)
        self.assertEqual(works_bool, True)
        works_bool = (prog0.opti_steps[0] > 0) and (prog1.opti_steps[0] == 0)
        self.assertEqual(works_bool, True)
        # Testing that opti processed was logged in FreeConstantsTable
        works_bool = (my_programs.free_consts.is_opti[0] == True) and (my_programs.free_consts.is_opti[1] == False)
        self.assertEqual(works_bool, True)
        works_bool = (my_programs.free_consts.opti_steps[0] > 0) and (my_programs.free_consts.opti_steps[1] == 0)
        self.assertEqual(works_bool, True)

        # Optimizing free constants of prog 1
        prog1.optimize_constants(X=X, y_target=y_target1)

        # Testing that opti processed was logged in Program
        works_bool = (prog0.is_opti[0] == True) and (prog1.is_opti[0] == True)
        self.assertEqual(works_bool, True)
        works_bool = (prog0.opti_steps[0] > 0) and (prog1.opti_steps[0] > 0)
        self.assertEqual(works_bool, True)
        # Testing that opti processed was logged in FreeConstantsTable
        works_bool = (my_programs.free_consts.is_opti[0] == True) and (my_programs.free_consts.is_opti[1] == True)
        self.assertEqual(works_bool, True)
        works_bool = (my_programs.free_consts.opti_steps[0] > 0) and (my_programs.free_consts.opti_steps[1] > 0)
        self.assertEqual(works_bool, True)

        # TEST CONSTANTS RECOVERY
        exp_tol = 1e-4

        # testing that constants are recovered in FreeConstantsTable
        obs_const0   = data_conversion_inv(my_programs.free_consts.values[0])
        works_bool = (np.abs(ideal_const_array0 - obs_const0) < exp_tol).all()
        self.assertEqual(works_bool, True)
        # testing that constants are recovered in program
        obs_const0   = data_conversion_inv(prog0.free_const_values)
        works_bool = (np.abs(ideal_const_array0 - obs_const0) < exp_tol).all()
        self.assertEqual(works_bool, True)

        # testing that constants are recovered in FreeConstantsTable (the first one does not matter)
        obs_const1   = data_conversion_inv(my_programs.free_consts.values[1])
        works_bool = (np.abs(ideal_const_array1[1:] - obs_const1[1:]) < exp_tol).all()
        self.assertEqual(works_bool, True)
        # testing that constants are recovered in program
        obs_const1   = data_conversion_inv(prog1.free_const_values)
        works_bool = (np.abs(ideal_const_array1[1:] - obs_const1[1:]) < exp_tol).all()
        self.assertEqual(works_bool, True)

        # testing that target y are reproduced
        exp_tol = 1e-6
        MSE_0 = data_conversion_inv(torch.mean((prog0(X) - y_target0) ** 2))
        works_bool = np.abs(MSE_0)<exp_tol
        self.assertEqual(works_bool, True)
        MSE_1 = data_conversion_inv(torch.mean((prog1(X) - y_target1) ** 2))
        works_bool = np.abs(MSE_1) < exp_tol
        self.assertEqual(works_bool, True)

        return None

if __name__ == '__main__':
    unittest.main(verbosity=2)
