import os

from langchain.prompts.chat import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
# from langchain.callbacks.base import CallbackManager
from langchain.callbacks.manager import AsyncCallbackManager

import gradio as gr

from dotenv import load_dotenv
load_dotenv()

# 設定プロンプト
character_setting = """You are ChatGPT, a large language model trained by OpenAI.
Carefully heed the user's instructions.
Respond using Markdown."""

# チャットプロンプトテンプレート
prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(character_setting),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{input}")
])

# チャットモデル
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo-0613", 
    max_tokens=512,
    temperature=0.2,
    streaming=True, 
    # callback_manager=CallbackManager([StreamingStdOutCallbackHandler()])
    callback_manager=AsyncCallbackManager([StreamingStdOutCallbackHandler()])
)

# メモリ
memory = ConversationBufferWindowMemory(k=3, return_messages=True)

# 会話チェーン
conversation = ConversationChain(memory=memory, prompt=prompt, llm=llm, verbose=True)

# フロントエンド
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
    chatbot = gr.Chatbot(height=600)
    msg = gr.Textbox()
    clear = gr.Button("Clear")

    def user(message, history):
        return "", history + [[message, None]]

    def chat(history):
        message = history[-1][0]
        response = conversation.predict(input=message)
        history[-1][1] = response
        return history

    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
        chat, chatbot, chatbot
    )
    clear.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch(debug=True)
