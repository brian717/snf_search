
# The following CDF was built from the PDF provided here: 
# https://www.rita.dot.gov/bts/sites/rita.dot.gov.bts/files/publications/omnistats/volume_03_issue_04/pdf/entire.pdf
DOT_AVERAGE_COMMUTE_CDF = {
    5: 29,
    10: 51,
    15: 68,
    20: 78,
    25: 85,
    30: 90,
    35: 93
}

def get_bisection(key1, key2, distance):
    """
    Compute a percentile rank for a given distance that lies between the distances 
    keyed in the DOT_AVERAGE_COMMUTE_CDF table. Assumes linear increase in CDF values.
    """
    score1 = DOT_AVERAGE_COMMUTE_CDF[key1] if key1 > 0 else 0
    score2 = DOT_AVERAGE_COMMUTE_CDF[key2]
    return (score2 - score1) * float(distance - key1) / (key2 - key1) + score1

    
def get_distance_percentile(distance):
    """
    Given a distance in miles, provides the percentage of the US population that commutes
    more than the given distance to work, on average. 
    """
    distances = DOT_AVERAGE_COMMUTE_CDF.keys()
    distances.sort()
    last_distance = 0
    for d in distances:
        if distance < d:
            return 100 - get_bisection(last_distance, d, distance)
        last_distance = d
    return 0

def compute_cdf(all_providers, metric, reverse = True):
    """Computes the CDF for a given metric across all providers. 
    
    Arguments:
    all_providers - A list of all providers to score against
    metric - A function that takes a provider and returns a number to analyze
    reverse - A boolean stating whether to sort the given metric in reverse order. Defaults to True
    """
    counts = [metric(p) for p in all_providers]
    counts.sort(reverse = reverse)
    cdf = {}
    for num in set(counts):
        cdf[num] = counts.index(num)
    return cdf
    
def deficiencies_cdf(all_providers):
    return compute_cdf(all_providers, lambda p: p.num_deficiencies, True)
    
def penalties_cdf(all_providers):
    return compute_cdf(all_providers, lambda p: p.num_penalties, True)
    
def rating_cdf(all_providers):
    return compute_cdf(all_providers, lambda p: p.overall_rating, False)

class ProviderScorer:
    def __init__(self, provider_repository, zipcode_repository):
        """ Initializes a ProviderScorer with a ProviderRepository and a ZipCodeReposiory."""
        all_providers = provider_repository.get_all_providers()
        self.num_providers = len(all_providers)
        self.r_cdf = rating_cdf(all_providers)
        self.p_cdf = penalties_cdf(all_providers)
        self.d_cdf = deficiencies_cdf(all_providers)
        self.zipcode_repository = zipcode_repository

    def populate_score(self, provider, zipcode):
        """Populates the score, lat, lng, and distance_miles fields on the given provider.
        
        Arguments:
            provider - The provider to score.
            zipcode - The zipcode to score distances against.
        """
        rating_percentile = 100 * self.r_cdf[provider.overall_rating] / self.num_providers
        deficiencies_percentile = 100 * self.d_cdf[provider.num_deficiencies] / self.num_providers
        penalties_percentile = 100 * self.p_cdf[provider.num_penalties] / self.num_providers
        distance = self.zipcode_repository.get_distance_between(provider.zip, zipcode)
        distance_percentile = get_distance_percentile(distance)
        criteria = [rating_percentile, deficiencies_percentile, penalties_percentile, distance_percentile]
        try:
            zip_mapping = self.zipcode_repository.get(provider.zip)
            provider.lat = zip_mapping.lat
            provider.lng = zip_mapping.lng
            provider.distance_miles = distance
        except KeyError:
            # Looks like there were some missing zip codes in the mapping csv...
            pass
        
        # Equally weighting scores at the moment... we can weigh things differently if 
        # we determine that one metric is more important than another
        provider.score = sum(criteria) / len(criteria)
    
    def populate_all_scores(self, providers, zipcode):
        """Populates scores and geographical information on all providers passed in."""
        for p in providers:
            self.populate_score(p, zipcode)