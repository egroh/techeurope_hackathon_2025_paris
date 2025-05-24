
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from huggingface_hub import login


class MathstralModel(object):
    def __init__(self):
        # Load the model and tokenizer
        model_name = "mistralai/Mathstral-7B-v0.1"

        access_token = "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" # token_for_paris_hackathon
        login(access_token)

        # pretrained_model_path = "./models/mathstral"
        # tokenizer_model_path = "./models/mathstral_tokenizer"
        # cache_dir = "./cache"

        model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto", torch_dtype=torch.bfloat16)
        # model.save_pretrained(pretrained_model_path)
        
        model = model.to(torch.device("cuda"))

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        # tokenizer.save_pretrained(tokenizer_model_path)

        self.model = model
        self.tokenizer = tokenizer

    def _format_prompt(self, prompt: str) -> str:
        prompt_formatted = prompt + "\n" +\
                            "Give step by step solution in the following format.\n" +\
                            "<step 1>\n<step 2>\n ... \n<step n>"
        return prompt_formatted
    
    def generate(self, prompt: str):
        # Encode the input prompt
        prompt = self._format_prompt(prompt)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        # Generate the response
        outputs = self.model.generate(**inputs, max_new_tokens=512)
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(response)
        return response