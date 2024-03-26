from __future__ import print_function
import time
import vantage
from vantage.rest import ApiException
from pprint import pprint
import json

# Configure OAuth2 access token for authorization: oauth2
configuration = vantage.Configuration()
configuration.access_token = 'JaoXQR2IDuvuZkkqx1rtsK7OQhOZxg7geOjSgqEDS9I'

# create an instance of the API class
api_instance = vantage.PricesApi(vantage.ApiClient(configuration))
provider_id = 'aws' # str | Query services for a specific provider. e.g. aws (optional)
service_id = 'aws-ec2'
page = 1 # int | The page of results to return. (optional)
max_pages = 2
limit = 1000 # int | The amount of results to return. The maximum is 1000 (optional)
instances = []
group_types = []
groups = {}

try:
    # api_response = api_instance.get_providers(page=page, limit=limit)
    # api_response = api_instance.get_services(provider_id=provider_id, page=page, limit=limit)
    while page < max_pages:
        api_response = api_instance.get_products(provider_id=provider_id, service_id=service_id, page=page, limit=limit)
        print("++++++++++++++++ %s +++++++++++++++++" % (page))
        for product in api_response.products:
            # print(product.name)
            instances.append(product.name)
            group_type, tshirt = product.name.split('.')
            group_types.append(group_type)

            if group_type not in groups.keys():
                groups[group_type] = [tshirt]
            else:
                groups[group_type].append(tshirt)
        page +=1

    outfile = 'aws_service_info/ec2_instances.json'
    with open(outfile,'w') as f:
        f.write(json.dumps({
            'instances': sorted(list(set(instances))),
            'families': sorted(list(set(group_types))),
            'groups': groups
        }, indent=4))
        print('written %s' % (outfile))

    # api_response = api_instance.get_prices(product_id) (id) (provider_id=provider_id, service_id=service_id, page=page, limit=limit)

except ApiException as e:
    print("Exception when calling PricesApi->get_services: %s\n" % e)