import os
import subprocess

def clone_repo(url: str):
    """Clone and optionally build a GitHub repository."""
    try:
        repo_name = url.split("/")[-1].replace(".git", "")
        target_dir = os.path.join(os.getcwd(), repo_name)
        log_path = os.path.join(target_dir, "build_report.log")

        if not os.path.exists(target_dir):
            print(f"⬇️ Cloning repository: {repo_name}")
            subprocess.run(["git", "clone", url], check=True)
        else:
            print(f"🔁 Repository already exists: {repo_name}")

        print("✅ Repository cloned successfully.")
        print("⚙️ Attempting setup...")

        setup_result = setup_repo(target_dir)

        if setup_result:
            print("✅ Build/setup completed successfully.")
        else:
            print(f"⚠️ Issues detected. See {log_path} for details.")

    except subprocess.CalledProcessError as e:
        print(f"❌ Git clone failed: {e}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")


def setup_repo(path: str) -> bool:
    """Try to set up cloned repo (pip install, etc)."""
    log_path = os.path.join(path, "build_report.log")
    success = True

    with open(log_path, "w") as log:
        try:
            if os.path.exists(os.path.join(path, "requirements.txt")):
                log.write("Installing requirements...\n")
                result = subprocess.run(
                    ["pip", "install", "-r", "requirements.txt"],
                    cwd=path,
                    capture_output=True,
                    text=True,
                )
                log.write(result.stdout)
                if result.returncode != 0:
                    log.write(result.stderr)
                    success = False
            elif os.path.exists(os.path.join(path, "setup.py")):
                log.write("Running setup.py install...\n")
                result = subprocess.run(
                    ["python3", "setup.py", "install"],
                    cwd=path,
                    capture_output=True,
                    text=True,
                )
                log.write(result.stdout)
                if result.returncode != 0:
                    log.write(result.stderr)
                    success = False
            else:
                log.write("No setup.py or requirements.txt found.\n")
                success = False

        except Exception as e:
            log.write(f"Error during setup: {str(e)}\n")
            success = False

    return success
