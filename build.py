# Command line build script for SoSSim, with various flags to control what stages are executed.

import argparse
import os

if __name__ == "__main__":
    # Parse the command line arguments and store them in args.
    parser = argparse.ArgumentParser(description='Build the SoSSim simulator.')
    parser.add_argument('--typecheck', default = False, action=argparse.BooleanOptionalAction, help = "Run code typecheck")
    parser.add_argument('--docs',      default = False, action=argparse.BooleanOptionalAction, help = "Generate documentation")
    parser.add_argument('--all',       default = False, action='store_true',                   help = "Run all build steps")

    args = parser.parse_args()

    # Build steps.

    # Typechecking.
    if args.typecheck or args.all:
        # Checking types. In principle, it does mypy source. However, to avoid trying to type check generated files under source/static, it is divided into several steps.
        # The client is type checked by transcrypt during the client build step, if the -ds flag is supplied.
        print("Run code typecheck")
        for root, dirs, files in os.walk("./source"):
            for file in files:
                # Type check all Python files, except those in the mesa subdirectory.
                if file.endswith(".py") and not root.endswith("mesa"):
                    path = os.path.join(root, file)
                    print(f"\nChecking {path}\n")
                    # TODO: Follow imports was skipped due avoid reporting typing errors in mesa. However, it may be too restrictive.
                    os.system(f"mypy --follow-imports skip {path}")

    # Documentation.
    if args.docs or args.all:
        print("Generate documentation")
        # Pdoc assumes that the top directory is on the path, so add it there.
        os.environ["PYTHONPATH"] = str(os.path.abspath("source"))
        os.system("pdoc ./source/capabilities ./source/model -o ./documentation")