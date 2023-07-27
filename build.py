# Command line build script for SoSSim, with various flags to control what stages are executed.

import argparse
import os
from pathlib import Path

import pdoc

if __name__ == "__main__":
    # Parse the command line arguments and store them in args.
    parser = argparse.ArgumentParser(description='Build the SoSSim simulator.')
    parser.add_argument('--typecheck', default = False, action = argparse.BooleanOptionalAction, help = "Run code typecheck")
    parser.add_argument('--docs',      default = False, action = argparse.BooleanOptionalAction, help = "Generate documentation")
    parser.add_argument('--pyconfig',  default = False, action = argparse.BooleanOptionalAction, help = "Generate pyscript configuration file")
    parser.add_argument('--all',       default = False, action = 'store_true',                   help = "Run all build steps")

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
                    os.system(f"mypy {path}")

    # Documentation.
    if args.docs or args.all:
        print("Generate documentation")
        source_dir = Path("source")
        target_dir = Path("documentation")
        # Remove existing files before generating new ones.
        for file in target_dir.glob("*"):
            file.unlink()
        # Configure and run pdoc on selected files
        pdoc.render.configure(docformat = "google")
        modules = list(source_dir.glob("*.py"))
        # The following code is based on pdoc.pdoc, but modified to skip files that causes an error.
        all_modules = {}
        for module_name in pdoc.extract.walk_specs(modules):
            try:
                all_modules[module_name] = pdoc.doc.Module.from_name(module_name)
            except Exception:
                print("Cannot document module", module_name)

        for module in all_modules.values():
            out = pdoc.render.html_module(module, all_modules)
            outfile = target_dir / f"{module.fullname.replace('.', '/')}.html"
            outfile.parent.mkdir(parents=True, exist_ok=True)
            outfile.write_bytes(out.encode())

        if index := pdoc.render.html_index(all_modules):
            (target_dir / "index.html").write_bytes(index.encode())

        if search := pdoc.render.search_index(all_modules):
            (target_dir / "search.js").write_bytes(search.encode())

    # Pyscript configuration file
    if args.pyconfig or args.all:
        print("Generate pyconfig.toml file")
        # Generate list of packages from requirements.txt
        with open("requirements.txt") as file:
            packages = file.readlines()
        # Clean the package representation and convert to a string
        packages = ", ".join(['"' + pkg.strip() + '"' for pkg in packages])
        # Generate list of python files by walking the directory tree under source.
        source_dir = Path("source")
        files = list(source_dir.glob("**/*.py"))
        # Clean the file representation and convert to a string
        files = ", ".join(['"' + file.relative_to("source").as_posix() + '"' for file in files if file.name != "sossim.py"])
        # Generate the output
        with Path("source/pyconfig.toml").open("w") as f:
            f.write("# Pyscript configuration file generated by build.py\n")
            f.write(f"packages = [{packages}]\n\n")
            f.write("terminal = false\n\n")
            f.write("[splashscreen]\n")
            f.write("enabled = false\n\n")
            f.write("[[fetch]]\n")
            f.write(f"files = [{files}]")
        """ 
        packages = ["networkx", "numpy", "pandas"]

terminal = false

[splashscreen]
enabled = false

[[fetch]]
files = ["agent.py", "capabilities.py", "domscript.py", "model.py", "space.py", "user_interface.py", "mesa/__init__.py", "mesa/agent.py", "mesa/datacollection.py", "mesa/model.py", "mesa/space.py", "mesa/time.py"]
"""