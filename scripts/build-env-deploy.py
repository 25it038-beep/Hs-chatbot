import os
import sys
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent.parent
    env_path = root_dir / "backend" / ".env"
    
    if not env_path.exists():
        print(f"Error: Local environment file not found at {env_path}")
        print("Please make sure you have created backend/.env and filled in your API keys.")
        sys.exit(1)
        
    print(f"Reading local environment from: {env_path}")
    env_vars = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip()
                
    print("\n" + "="*50)
    print("RENDER.YAML FORMAT (for render.yaml blueprint)")
    print("="*50)
    for key, val in env_vars.items():
        is_secret = any(s in key.lower() for s in ["key", "secret", "token", "password"])
        val_str = "*****" if is_secret else val
        print(f"      - key: {key}")
        print(f"        value: \"{val_str}\"")
        
    deploy_env_path = root_dir / "backend" / ".env.deploy"
    with open(deploy_env_path, "w", encoding="utf-8") as f:
        f.write("# Cleaned environment variables for deployment\n")
        f.write("# Generated automatically from backend/.env\n\n")
        for key, val in env_vars.items():
            f.write(f"{key}={val}\n")
            
    print("\n" + "="*50)
    print(f"CLEANED DEPLOY FILE WRITTEN TO: {deploy_env_path}")
    print("This file contains your raw keys, but is safely ignored by .gitignore.")
    print("="*50)

if __name__ == "__main__":
    main()
