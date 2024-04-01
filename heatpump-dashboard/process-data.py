# import csv

# def process_data(input_file, output_file):
#     with open(input_file, 'r', newline='', encoding='utf-8') as f:
#         reader = csv.DictReader(f)
        
#         with open(output_file, 'w', newline='', encoding='utf-8') as out_file:
#             writer = csv.writer(out_file)
#             writer.writerow(['city_state', 'lat', 'lng'])  
            
#             for row in reader:
#                 city_state = f"{row['city']}, {row['state_name']}"
#                 lat = row['lat']
#                 lng = row['lng']
#                 writer.writerow([city_state, lat, lng])

# if __name__ == "__main__":
#     input_file = '.venv/heatpump-dashboard/data-raw/uscities.csv'
#     output_file = '.venv/heatpump-dashboard/data/cities.csv'
#     process_data(input_file, output_file)

import csv

def process_data(input_file, output_file):
    city_state_set = set()  # To store unique city_state values
    
    with open(input_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as out_file:
            writer = csv.writer(out_file)
            writer.writerow(['city_state', 'lat', 'lng'])  # Writing the header
            
            for row in reader:
                city_state = f"{row['city']}, {row['state_name']}"
                population = int(row['population'].replace(',', ''))
                if population >= 10000 and city_state not in city_state_set:
                    lat = row['lat']
                    lng = row['lng']
                    writer.writerow([city_state, lat, lng])
                    city_state_set.add(city_state)

if __name__ == "__main__":
    input_file = '.venv/heatpump-dashboard/data-raw/uscities.csv'
    output_file = '.venv/heatpump-dashboard/data/cities.csv'
    process_data(input_file, output_file)
