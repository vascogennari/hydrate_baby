
def process(user_input, logger):

    # Check the user input is correctly passed
    def require_float(key):
        value = user_input.get(key)
        if value is None or value.strip() == "":
            raise ValueError(f"Missing value for '{key}'")
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"Invalid number for '{key}': {value}")

    pars = dict()
    # Input values from user. Defaults are in the index.html file
    pars['weight_actual'] = require_float('weight_actual') # Current weight [kg]
    pars['K_actual'] = require_float('K_actual') # Current K concentration [mEq/l]
    pars['Na_actual'] = require_float('Na_actual') # Current Na concentration [mEq/l]

    # Treat multiple option separately.
    # Try to parse floats if provided, or None if empty
    weight_nominal_raw = user_input.get('weight_nominal', '').strip()
    who_scale_raw = user_input.get('who_scale', '').strip()
    pars['weight_nominal'] = float(weight_nominal_raw) if weight_nominal_raw else None
    pars['who_scale'] = float(who_scale_raw) if who_scale_raw else None

    pars['Na_necessary_nominal'] = float(user_input.get('Na_necessary_nominal', 3)) # nominal necessary values Na [mEq/l]
    pars['K_necessary_nominal'] = pars['Na_necessary_nominal'] / 2 # Nominal necessary values K [mEq/l]

    pars['Na_correction_factor'] = 0.6 # Deficit correction factor Na []
    pars['K_correction_factor'] = 0.4 # Deficit correction factor K []

    pars['Na_maximum_value'] = 135. # Maximum Na values for hyponatremia. In [mEq/l]
    pars['K_maximum_value'] = 3.5 # Maximum K values for hypopotassemia. In [mEq/l]

    # Control input values
    check_input_values(pars, logger)

    dosage = ComputeDosage(pars)
    results = dosage.compute_somministration(pars)
    return results


def check_input_values(pars, logger):

    def compute_dehydratation(weight_nominal, weight):
        fraction = ( weight_nominal - weight ) / weight_nominal
        return fraction * 100
    
    # Control multiple options for dehydratation
    if pars['weight_nominal'] is None and pars['who_scale'] is None:
        raise ValueError("Please provide either the current weight or the WHO scale value to compute the dehydratation percentage.")
    
    elif pars['weight_nominal'] is not None:
        if pars['who_scale'] is not None:
            logger.info("Both current weight and WHO scale were provided. Using current weight to compute the dehydratation percentage.")
        else:
            logger.info("Using current weight to compute the dehydratation percentage.")

        pars['dehydratation_percentage'] = compute_dehydratation(pars['weight_nominal'], pars['weight_actual'])
        if pars['weight_actual'] > pars['weight_nominal']:
            raise ValueError('The weight of the patient dehydrated needs to be less than its normal weight.')
        if pars['weight_nominal'] >= 10:
            raise ValueError('This calculator uses formulae valid for the patient weight to be less than 10 kg.')
        
    elif pars['weight_nominal'] is None and pars['who_scale'] is not None:
        logger.info("Using WHO scale to compute the dehydratation percentage.")
        pars['dehydratation_percentage'] = pars['who_scale']

    if pars['dehydratation_percentage'] >= 12:
        raise ValueError('ALERT! The patient dehydratation is more than severe (>12%). Please consider a manual treatment.')
    
    # Control electrolytes
    if pars['Na_actual'] >= pars['Na_maximum_value']:
        raise ValueError('The Na concentration is normal and needs no correction. Please consider a manual treatment.')
    if pars['K_actual'] >= pars['K_maximum_value']:
        raise ValueError('The K concentration is normal and needs no correction. Please consider a manual treatment.')


class ComputeDosage:

    def __init__(self, pars):
        self.pars = pars

    def compute_necessary_volume(self, weight):
        return 100 * weight # Current weight [kg] * 100 [ml]

    def compute_deficit_volume(self, weight, dehydratation):
        return weight * dehydratation * 10 # Current weight [kg] * dehydratation percetage [%] * 10

    def compute_necessary_electrolites(self, reference_value, weight):
        return reference_value * weight # Reference value [mEq/l] * current weight [kg]

    def compute_deficit_electrolites(self, value, weight, correction, value_nominal):
        fraction =  value_nominal - value # Target value [mEq/l] - current value [mEq/l]
        return fraction * weight * correction # Value difference [mEq/l] * current weight [kg] * electrolite correction factor []
    
    def compute_somministration(self, pars):

        values = dict()
        values['first 8h'] = {}
        values['last 16h'] = {}

        effective_necessary_volume = self.compute_necessary_volume(pars['weight_actual'])
        effective_deficit_volume = self.compute_deficit_volume(pars['weight_actual'], pars['dehydratation_percentage'])
        effective_necessary_electrolites_Na = self.compute_necessary_electrolites(pars['Na_necessary_nominal'], pars['weight_actual'])
        effective_necessary_electrolites_K = self.compute_necessary_electrolites(pars['K_necessary_nominal'],  pars['weight_actual'])
        effective_deficit_electrolites_Na = self.compute_deficit_electrolites(pars['Na_actual'], pars['weight_actual'], pars['Na_correction_factor'], pars['Na_maximum_value'])
        effective_deficit_electrolites_K = self.compute_deficit_electrolites(pars['K_actual'],  pars['weight_actual'], pars['K_correction_factor'],  pars['K_maximum_value'])

        variables = {
            "total volume": effective_necessary_volume + effective_deficit_volume,
            "total electrolites Na": effective_necessary_electrolites_Na + effective_deficit_electrolites_Na,
            "total electrolites K": effective_necessary_electrolites_K + effective_deficit_electrolites_K}

        for name, value in variables.items():
            values['first 8h'][name] = value / 3
            values['last 16h'][name] = value * 2 / 3

        return values
