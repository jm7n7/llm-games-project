import torch
import diffusers
import transformers
import accelerate
import sys
#pip install torch==2.3.1 diffusers==0.29.0 transformers==4.41.2 accelerate==0.30.1

# --- Step 1: Verify the environment from within the script ---
print("--- Diagnosing Environment ---")
print(f"Python Executable: {sys.executable}")
print(f"PyTorch version: {torch.__version__}")
print(f"Diffusers version: {diffusers.__version__}")
print(f"Transformers version: {transformers.__version__}")
print(f"Accelerate version: {accelerate.__version__}")
print("----------------------------\n")

# --- Step 2: Attempt to load the model with a basic configuration ---
try:
    print("Attempting to load the Stable Diffusion model...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Using a simpler, more compatible loading method first
    pipe = diffusers.StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        # We are intentionally leaving out torch_dtype for this test
    )
    pipe = pipe.to(device)
    
    print("\n✅ Model loaded successfully!")

    # --- Step 3: Generate an image ---
    prompts = [
    "a hand-drawn, two dimensional image of a renaisaunce era crown in graphite",
    "an oil painting of a medievil castle turret that has been bombarded by artillery and is crumbling",
    "a classic Walt Disney style drawing for a robot chess coach logo"
    ]

    for i, prompt in enumerate(prompts):
        print(f"Generating image for prompt: '{prompt}'")
        
        # Generate the image
        image = pipe(prompt).images[0]
        
        # Save the image
        image.save(f"output_{i+1}.png")
        print(f"Saved image as output_{i+1}.png")

    print("Image generation complete.")

except Exception as e:
    print(f"\n❌ An error occurred: {e}")
    print("\nIf the error is the same 'offload_state_dict' issue, the version mismatch is confirmed by the diagnostic printout above.")