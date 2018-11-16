from klibs.KLIndependentVariable import IndependentVariableSet

SearchSpaceAndTime_ind_vars = IndependentVariableSet()

SearchSpaceAndTime_ind_vars.add_variable("search_type", str, ['space', 'time'])
SearchSpaceAndTime_ind_vars.add_variable("cell_count", int, [25,36,49,64])
SearchSpaceAndTime_ind_vars.add_variable("distractor_distractor", str, ["homo", "hetero"])
SearchSpaceAndTime_ind_vars.add_variable("target_distractor", str, ["homo", "hetero"])