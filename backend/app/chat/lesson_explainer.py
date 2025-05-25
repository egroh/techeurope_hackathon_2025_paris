from huggingface_hub import InferenceApi

# ─── Configuration ─────────────────────────────────────────────────────────────
# Set this in your environment before running:
#   export HF_HUB_TOKEN="your_hf_api_key"
HF_TOKEN = "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"

if not HF_TOKEN:
    raise RuntimeError("Please set the HF_HUB_TOKEN env var to your HuggingFace API token")

# Create an Inference API client for Mistral 7B v0.3
inference = InferenceApi(
    repo_id="mistralai/Mistral-7B-v0.3",
    token=HF_TOKEN,
    task="text-generation"
)

def explain_lesson(
    textual_prompt: str | None = None,
    ocr_text:      str | None = None,
    max_tokens:    int  = 1024,
    temperature:    float = 0.6,
    top_p:          float = 0.9
    ) -> str:
    """
    Builds a combined prompt from optional textual_prompt and ocr_text,
    sends it to Mistral-7B-v0.3, and returns the generated explanation.
    """
    if not (textual_prompt or ocr_text):
        raise ValueError("You must provide at least one of textual_prompt or ocr_text.")

    # Combine contexts
    parts: list[str] = []
    if ocr_text:
        parts.append("Extracted text from your uploaded document:\n" + ocr_text)
    if textual_prompt:
        parts.append("User Prompt:\n" + textual_prompt)


    context = "\n\n".join(parts)

    # Final prompt for the model
    prompt = (
        "You are a friendly, patient tutor. Explain the following lesson content "
        "in clear, accessible terms (as if to a student seeing this for the first time). "
        "After your explanation, invite them to ask follow-up questions.\n\n"
        f"{context}\n\n"
        "=== Begin explanation ===\n"
    )

    # Call the HF Inference API
    response = inference(
        prompt,
        parameters={
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "return_full_text": False
        }
    )
    # The HF Inference API returns a dict with a 'generated_text' field
    return response["generated_text"].strip()

if __name__ == "__main__":
    # A minimal test to see if your explain_lesson function is wired up correctly.
    # Make sure you’ve set HF_HUB_TOKEN in your environment first!
    sample_prompt = "Explain why the angles of a triangle sum to 180 degrees."
    try:
        explanation = explain_lesson(textual_prompt=sample_prompt)
        print("✅ explain_lesson returned:\n")
        print(explanation)
    except Exception as e:
        print("❌ explain_lesson failed with:", e)
