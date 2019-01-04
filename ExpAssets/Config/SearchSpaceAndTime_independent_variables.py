from klibs.KLIndependentVariable import IndependentVariableSet

SearchSpaceAndTime_ind_vars = IndependentVariableSet()

SearchSpaceAndTime_ind_vars.add_variable("set_size", int, [8,12,16,20])
SearchSpaceAndTime_ind_vars.add_variable("distractor_distractor", str, ["homo", "hetero"])
SearchSpaceAndTime_ind_vars.add_variable("target_distractor", str, ["homo", "hetero"])
SearchSpaceAndTime_ind_vars.add_variable("present_absent", str, ['present', 'absent'])