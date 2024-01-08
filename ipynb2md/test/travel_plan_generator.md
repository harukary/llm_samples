### Prerequisites


```python
# !pip install googlemaps folium
# !pip install --upgrade pip
```


```python
from dotenv import find_dotenv,load_dotenv
load_dotenv(find_dotenv())
```




    True



### List up attractions using LLM


```python
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel,Field
from typing import Optional
```


```python
import langchain
langchain.__version__
```




    '0.0.232'




```python
llm = ChatOpenAI(model='gpt-3.5-turbo-16k',temperature=0.1)

template = """\
## Instruction
List up {k} attractions in {place}.
{user_profile}

## Output
{format_instruction}
"""

class Attraction(BaseModel):
    name: str = Field(description='The name of attraction')
    country: str = Field(description='The country the attraction located')
    city: str = Field(description='The city the attraction located')

    description: str = Field(description='Description of the attraction. More than 1000 words.')
    duration: float = Field(description='Duration time of the attraction. Hours.')

    lat: Optional[float] = Field(description='latitude of the attraction')
    lng: Optional[float] = Field(description='longitude of the attraction')

class Attractions(BaseModel):
    data: list[Attraction] = Field(description='List of Atrractions')

parser = PydanticOutputParser(pydantic_object=Attractions)

prompt = ChatPromptTemplate.from_template(
    template=template,
    partial_variables={'format_instruction':parser.get_format_instructions()},
)
```


```python
chain = LLMChain(llm=llm,prompt=prompt,output_parser=parser)#,verbose=True)
```


```python
user_profile = "This is my first visit in here."
res = chain.run(place='London',k=3,user_profile=user_profile)
```


```python
data = res.dict()['data']
```


```python
data[0]
```




    {'name': 'Tower of London',
     'country': 'United Kingdom',
     'city': 'London',
     'description': 'The Tower of London is a historic castle located on the north bank of the River Thames in central London. It was founded towards the end of 1066 as part of the Norman Conquest of England. The White Tower, which gives the entire complex its name, was built by William the Conqueror in 1078 and was a resented symbol of oppression, inflicted upon London by the new ruling elite. The castle was used as a prison from 1100 until 1952, although that was not its primary purpose. A grand palace early in its history, it served as a royal residence. As a whole, the Tower is a complex of several buildings set within two concentric rings of defensive walls and a moat. There were several phases of expansion, mainly under Kings Richard the Lionheart, Henry III, and Edward I in the 12th and 13th centuries. The general layout established by the late 13th century remains despite later activity on the site.',
     'duration': 2.0,
     'lat': 51.5081,
     'lng': -0.0761}



### Get latitude and longitude using GoogleMaps API (Not necessary)


```python
import googlemaps,os,json
gmaps = googlemaps.Client(key=os.environ['GOOGLE_MAPS_API_KEY'])
```


```python
for i,d in enumerate(data):
    print(i,d['name'],'-'*30)
    geocode_result = gmaps.geocode(d['name'])
    gmap_res = geocode_result[0]["geometry"]["location"]
    print('GoogleMaps:',gmap_res["lat"],gmap_res["lng"])
    print('ChatGPT:',d["lat"],d["lng"])
    d['lat'],d['lng'] = gmap_res['lat'],gmap_res['lng']
```

    0 Tower of London ------------------------------
    GoogleMaps: 51.50811239999999 -0.0759493
    ChatGPT: 51.5081 -0.0761
    1 British Museum ------------------------------
    GoogleMaps: 51.5194133 -0.1269566
    ChatGPT: 51.5194 -0.1269
    2 Buckingham Palace ------------------------------
    GoogleMaps: 51.501364 -0.14189
    ChatGPT: 51.5014 -0.1419


### Get directions using GoogleMaps API


```python
# https://qiita.com/shin1007/items/8f31188b9ac83be9e738
def decode_polyline(enc: str):
    """
    Parameters
    ----------
    enc : str
        encoded string of polyline, which can be aquired via Google Maps API.

    Returns
    -------
    result : list
        each element in `result` contains pair of latitude and longitude.
    """
    if enc == None or enc == '':
        return [[0, 0]]

    result = []
    polyline_chars = list(enc.encode())
    current_latitude = 0
    current_longitude = 0
    try:
        index = 0
        while index < len(polyline_chars):
            # calculate next latitude
            total = 0
            shifter = 0

            while True:
                next5bits = int(polyline_chars[index]) - 63
                index += 1
                total |= (next5bits & 31) << shifter
                shifter += 5
                if not(next5bits >= 32 and index < len(polyline_chars)):
                    break

            if (index >= len(polyline_chars)):
                break

            if((total & 1) == 1):
                current_latitude += ~(total >> 1)
            else:
                current_latitude += (total >> 1)

            # calculate next longitude
            total = 0
            shifter = 0
            while True:
                next5bits = int(polyline_chars[index]) - 63
                index += 1
                total |= (next5bits & 31) << shifter
                shifter += 5
                if not(next5bits >= 32 and index < len(polyline_chars)):
                    break

            if (index >= len(polyline_chars) and next >= 32):
                break

            if((total & 1) == 1):
                current_longitude += ~(total >> 1)
            else:
                current_longitude += (total >> 1)

            # add to return value
            pair = [current_latitude / 100000, current_longitude / 100000]
            result.append(pair)

    except:
        pass
    return result
```


```python
from datetime import datetime, timedelta
now = datetime.strptime('2023/08/01 09:00','%Y/%m/%d %H:%M')

routes = []
first_trans_min = 30
print(now.strftime('%H:%M'), f"Going to {data[0]['name']}")
print('  ',f'Duration {str(int(first_trans_min))} minutes')
now += timedelta(minutes=first_trans_min)

for i in range(len(data)-1):
    # print(now)
    directions_result = gmaps.directions(
        data[i]['name'],
        data[i+1]['name'],
        mode="transit",
        departure_time=now
    )
    # print('directions_result:',directions_result[0]['legs'][0]['duration'])#.keys())
    duration_attraction_hour = data[i]['duration']
    print(now.strftime('%H:%M'), data[i]['name'])
    print('  ',f'Spent {"{:.1f}".format(duration_attraction_hour)} hours')
    now += timedelta(hours=duration_attraction_hour)
    
    duration_direction_sec = directions_result[0]['legs'][0]['duration']['value']
    print(now.strftime('%H:%M'), f"Going to {data[i]['name']}")
    print('  ',f'Duration {str(int(duration_direction_sec/60))} minutes')
    now += timedelta(seconds=duration_direction_sec)
    
    # print(now)
    steps = []
    for j,s in enumerate(directions_result[0]['legs'][0]['steps']):
        # print(j,'-'*30)
        steps.append({
            'polyline': decode_polyline(s['polyline']['points']),
            'travel_mode': s['travel_mode'],
            'duration': s['duration']['text'],
            'duration_sec': s['duration']['value']
        })
    routes.append(steps)
    # break
print(now.strftime('%H:%M'), "End")
```

    09:00 Going to Tower of London
       Duration 30 minutes
    09:30 Tower of London
       Spent 2.0 hours
    11:30 Going to Tower of London
       Duration 30 minutes
    12:00 British Museum
       Spent 3.0 hours
    15:00 Going to British Museum
       Duration 18 minutes
    15:18 End



```python
import folium
from branca.element import Figure
import pandas as pd
import numpy as np

color_map = {
    'WALKING': '#0000ff',
    'TRANSIT': '#ff0000',
}
```


```python
lat = np.mean([d['lat'] for d in data],)
lng = np.mean([d['lng'] for d in data],)
map = folium.Map(location=[lat,lng], zoom_start=14)

for d in data:
    folium.Marker(location=[d['lat'], d['lng']], popup=f"{d['name']} ({d['duration']})").add_to(map)

for i,steps in enumerate(routes):
    for step in steps:
        # print(len(step['polyline']))
        folium.vector_layers.PolyLine(
            locations=step['polyline'], popup=f'{step["travel_mode"]} ({step["duration"]})', color=color_map[step['travel_mode']]
        ).add_to(map)
    # break

fig = Figure(width=800, height=600)
fig.add_child(map)
```




![HTML output](resources/output_18_0.png)


