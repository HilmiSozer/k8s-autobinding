import argparse
import subprocess
import sys
import os
import yaml 


def run_command(cmd):
    """Helper function to run a shell command and handle errors."""
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}")
        print(e.stderr.strip())
        sys.exit(1)


def create_service_account(username, role, namespace, dry_run):
    """Creates a service account, binds it to a role, and creates/annotates a secret in Kubernetes."""

    dry_run_flag = ["--dry-run=client"] if dry_run else []

    # Step 1: Create the namespace (if it doesn't already exist)
    print(f"Ensuring namespace '{namespace}' exists...")
    ensure_namespace_cmd = ["kubectl", "get", "namespace", namespace]
    try:
        run_command(ensure_namespace_cmd)
        print(f"Namespace '{namespace}' already exists.")
    except SystemExit:
        create_ns_cmd = ["kubectl", "create", "namespace", namespace] + dry_run_flag
        run_command(create_ns_cmd)
        print(f"Namespace '{namespace}' created successfully.")

    # Step 2: Create the service account
    print(f"Creating service account '{username}' in namespace '{namespace}'...")
    create_sa_cmd = ["kubectl", "create", "serviceaccount", username, "--namespace", namespace] + dry_run_flag
    run_command(create_sa_cmd)
    print(f"Service account '{username}' created successfully.")

    # Step 3: Bind the service account to the specified role
    print(f"Binding service account '{username}' to role '{role}'...")
    bind_role_cmd = [
        "kubectl", "create", "rolebinding", f"{username}-{role}-binding",
        "--clusterrole", role, f"--serviceaccount={namespace}:{username}",
        "--namespace", namespace
    ] + dry_run_flag
    run_command(bind_role_cmd)
    print(f"Service account '{username}' bound to role '{role}' successfully.")

    # Step 4: Create a secret for the service account
    print(f"Creating a secret for the service account '{username}'...")
    secret_name = f"{username}-token"
    secret_yaml = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": secret_name,
            "namespace": namespace,
            "annotations": {
                "kubernetes.io/service-account.name": username
            }
        },
        "type": "kubernetes.io/service-account-token"
    }

    secret_file = f"{secret_name}.yaml"
    with open(secret_file, "w") as f:
        yaml.dump(secret_yaml, f)
    print(f"Generated secret YAML file: {secret_file}")

    # Apply the secret using kubectl
    create_secret_cmd = ["kubectl", "apply", "-f", secret_file] + dry_run_flag
    run_command(create_secret_cmd)
    print(f"Secret '{secret_name}' created in namespace '{namespace}' successfully.")

    # Clean up the YAML file if not in dry-run mode
    if not dry_run:
        os.remove(secret_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a Kubernetes service account and bind it to a role.")
    parser.add_argument("--username", required=True, help="The name of the service account to create.")
    parser.add_argument(
        "--role",
        required=True,
        choices=["product-team-role", "lead-developer-team-role", "cs-team-role", "operator"],
        help="The role to bind the service account to."
    )
    parser.add_argument("--namespace", default="staging", help="The namespace to use (default: 'staging').")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the commands without making changes.")

    args = parser.parse_args()
    create_service_account(args.username, args.role, args.namespace, args.dry_run)
