import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trainer import Trainer

def main():
    print("Gothic 1 Remake Trainer v1.0 (Python)")
    print("======================================")

    # Locate offsets.json relative to this file
    config_path = os.path.join(os.path.dirname(__file__), "offsets.json")
    if not os.path.exists(config_path):
        print("[!] offsets.json not found.")
        return

    trainer = Trainer()
    if not trainer.initialize(config_path):
        input("Initialization failed. Press Enter to exit.")
        return

    trainer.run()

if __name__ == "__main__":
    main()
