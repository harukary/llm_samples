from dotenv import find_dotenv,load_dotenv; _=load_dotenv(find_dotenv())

import json, os, datetime, requests
from tzlocal import get_localzone
from langchain.agents import AgentType, initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.tools import BaseTool, StructuredTool, Tool, tool
from langchain.prompts import MessagesPlaceholder
from langchain.prompts.chat import SystemMessage
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel, Field
from typing import Union, Any, Optional, Type
from enum import Enum
import googlemaps; gmaps = googlemaps.Client(key=os.environ['GOOGLE_MAPS_API_KEY'])

## Get current datetime
def get_now():
    now = datetime.datetime.now().replace(tzinfo=get_localzone())
    return now.strftime('%Y-%m-%d %H:%M %z')
get_current_datetime_tool = StructuredTool.from_function(
    func = get_now,
    # name='CurrentLocationGetter',
    description='You can use to get current datetime with no input.',
)

## Get current loc
def get_current_location():
    geo_request_url = 'https://get.geojs.io/v1/ip/geo.json'
    data = requests.get(geo_request_url).json()
    return {'latitude': data['latitude'],'longitude': data['longitude']}
get_current_location_tool = StructuredTool.from_function(
    func = get_current_location,
    description='You can get current location with no input.',
)
# print(json.dumps(get_current_location(),indent=2,ensure_ascii=False))

## Find place
def simplified_place_dict(res):
    r = res[0]
    return {
        'address': r['formatted_address'],
        'location': r['geometry']['location'],
        'types': r['types']
    }
def find_place_with_text_func(query: str):
    places_result = gmaps.find_place(query,input_type='textquery')
    geocode_results = [
        gmaps.geocode(place_id=r['place_id'])
        for r in places_result['candidates']
    ]
    return [simplified_place_dict(r) for r in geocode_results]
# print(find_place_with_text_func(query='Tower of London'))
find_place_tool_description = """\
A Find Place request takes a text input, and returns a place.
The text input can be any kind of Places data, for example,
a name, address, or phone number.
"""
find_place_tool = Tool.from_function(
    func = find_place_with_text_func,
    name='PlaceSearch',
    description=find_place_tool_description,
)

## Get directions
class Mode(Enum):
    DRIVING = "driving"
    WALKING = "walking"
    BYCYCLING = "bicycling"
    TRANSIT = "transit"

class DirectionsInput(BaseModel):
    origin: Union[str,dict] = Field(
        description='The address in string or latitude/longitude in dict from which you wish to calculate directions.'
    )
    destination: Union[str,dict] = Field(
        description='The address in string or latitude/longitude in dict from which you wish to calculate directions.'
    )
    mode: Mode = Field(
        description='Specifies the mode of transport to use when calculating directions.'
    )
    departure_time: Optional[str] = Field(
        description="Specifies the desired time of departure. Note: you can't specify both departure_time and arrival_time. The format must be \"%Y/%m/%d %H:%M %z\" (ex. \"2023/01/01 09:00 +0100\")."
    )
    arrival_time: Optional[str] = Field(
        description="Specifies the desired time of arrival for transit directions. Note: you can't specify both departure_time and arrival_time. The format must be \"%Y/%m/%d %H:%M %z\" (ex. \"2023/01/01 09:00 +0100\")."
    )

def simplified_directions_dict(res):
    r = res['legs'][0]
    return {
        'arrival_time': r['arrival_time']['text'] if 'arrival_time' in r.keys() else None,
        'departure_time': r['departure_time']['text'] if 'departure_time' in r.keys() else None,
        'distance': r['distance']['text'] if 'distance' in r.keys() else None,
        'duration': r['duration']['text'] if 'duration' in r.keys() else None,
        'steps': [
            {
                'distance': s['distance']['text'],
                'duration': s['duration']['text'],
                'travel_mode': s['travel_mode'],
                "instruction": s['html_instructions'],
                'transit_details': {
                    'arrival_stop': s['transit_details']['arrival_stop'],
                    'departure_stop': s['transit_details']['departure_stop'],
                } if 'transit_details' in s.keys() else None
            }
            for s in r['steps']
        ]
    }

class DirectionsTool(BaseTool):
    name = "Directions"
    description = "Get directions between an origin point and a destination point."
    args_schema: Type[DirectionsInput] = DirectionsInput

    def _run(self, origin, destination, mode, departure_time=None, arrival_time=None):
        print(self.datetime_to_timestamp(departure_time))
        directions_result = gmaps.directions(
            origin=origin,
            destination=destination,
            mode=mode.value,
            departure_time=self.datetime_to_timestamp(departure_time),
            arrival_time=self.datetime_to_timestamp(arrival_time)
        )
        # print(json.dumps(geocode_results,indent=2,ensure_ascii=False))
        return [simplified_directions_dict(r) for r in directions_result]

    async def _arun(self, origin, destination, mode):
        return self._run(origin, destination, mode)

    def datetime_to_timestamp(self,datetime_str):
        if datetime_str is None:
            return None
        dt = self.create_datetime(datetime_str) # datetime.datetime.strptime(datetime_str,'%Y-%m-%d %H:%M %z')
        # dt = dt.astimezone(get_localzone())
        return int(dt.timestamp())
    
    @staticmethod
    def create_datetime(input_string):
        formats = ["%Y/%m/%d %H:%M %z", "%Y-%m-%d %H:%M %z"]
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(input_string, fmt)
                return dt
            except ValueError:
                pass
        raise ValueError("Input string does not match any supported format")

get_direction_tool = DirectionsTool()

## Agent
llm = ChatOpenAI(temperature=0)
agent_kwargs = {
    "extra_prompt_messages": [
        MessagesPlaceholder(variable_name="memory")
    ],
    "system_message": SystemMessage(content=f'Current time: {get_now()}')
}
memory = ConversationBufferMemory(memory_key="memory", return_messages=True)
tools = [
    # get_current_datetime_tool,
    get_current_location_tool,
    find_place_tool,
    get_direction_tool
]

gmaps_agent = initialize_agent(
    tools, llm, agent=AgentType.OPENAI_FUNCTIONS,
    memory=memory, agent_kwargs=agent_kwargs,
    verbose=True
)

# フロントエンド
import gradio as gr
css = """
.gradio-container {background-color: #7494C0}
.message.user{
    background: #8DE055 !important;
}
.message.assistant{
    background: #EDF1EE !important;
}
"""

with gr.Blocks(css=css) as demo:
    # コンポーネント
    chatbot = gr.Chatbot(height=800)
    msg = gr.Textbox()
    clear = gr.Button("Clear")

    def user(message, history):
        return "", history + [[message, None]]

    def chat(history):
        message = history[-1][0]
        response = gmaps_agent.run(message)
        history[-1][1] = response
        return history

    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
        chat, chatbot, chatbot
    )
    clear.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch(debug=True)
