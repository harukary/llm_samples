## llama.cpp

git clone https://github.com/ggerganov/llama.cpp.git

cd llama.cpp

make


## nekomata
https://huggingface.co/mmnga/rinna-nekomata-14b-instruction-gguf/resolve/main/rinna-nekomata-14b-instruction-q4_0.gguf?download=true

./main -m '../nekomata/rinna-nekomata-14b-instruction-q2_K.gguf' -n 128 --temp 0.5 -p '### 指示:次の日本語を英語に翻訳してください。\n\n### 入力: 大規模言語モデル（だいきぼげんごモデル、英: large language model、LLM）は、多数のパラメータ（数千万から数十億）を持つ人工ニューラルネットワークで構成されるコンピュータ言語モデルで、膨大なラベルなしテキストを使用して自己教師あり学習または半教師あり学習によって訓練が行われる。 \n\n### 応答:'