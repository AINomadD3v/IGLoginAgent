{
  description = "Development environment for the IGLoginAgent project";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    uiautomator2.url = "path:/home/ai-dev/CustomLibraries/uiautomator2-nix";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    uiautomator2,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfreePredicate = pkg: builtins.elem (nixpkgs.lib.getName pkg) [];
      };

      python = pkgs.python313;

      pythonOverridden = python.override {
        packageOverrides = self: super: {
          adbutils = super.buildPythonPackage rec {
            pname = "adbutils";
            version = "2.9.2";
            format = "pyproject";
            src = super.fetchPypi {
              inherit pname version;
              sha256 = "sha256-beaLQULFTfTb6gckApnAUnFiUxoI6Lr8NsP9GsnEKR4=";
            };
            nativeBuildInputs = with super; [setuptools wheel pbr retry2];
            # --- FIX IS HERE: Added 'deprecation' back ---
            propagatedBuildInputs = with super; [
              requests
              deprecation # This was the missing dependency
              whichcraft
              packaging
              pillow
            ];
            doCheck = false;
          };

          pyairtable = super.buildPythonPackage rec {
            pname = "pyairtable";
            version = "3.1.1";
            format = "setuptools";
            src = super.fetchPypi {
              inherit pname version;
              sha256 = "sha256-sYX+8SEZ8kng5wSrTksVopCA/Ikq1NVRoQU6G7YJ7y4=";
            };
            propagatedBuildInputs = with super; [requests inflection pydantic];
            doCheck = false;
          };

          uiautomator2 = super.buildPythonPackage rec {
            pname = "uiautomator2";
            version = "3.2.0";
            format = "pyproject";
            src = uiautomator2.packages.${system}.src;
            nativeBuildInputs = with super; [setuptools wheel];
            propagatedBuildInputs = with super; [
              self.adbutils
              requests
              lxml
              pillow
              retry2
            ];
            postPatch = ''
              echo "Patching version into uiautomator2..."
              sed -i "s/__version__ = .*/__version__ = \"${version}\"/" uiautomator2/version.py
            '';
            doCheck = false;
            pythonImportsCheck = ["uiautomator2"];
          };
        };
      };

      nixpkgspythondepnames = [
        # Core functionality
        "pyyaml"
        "requests"
        "lxml"
        "pillow"
        "python-dotenv"
        "beautifulsoup4"
        "logzero"

        # Dependencies of custom packages
        "packaging"
        "whichcraft"
        "pbr"
        "inflection"
        "pydantic"
        "deprecation" # Also add it to the main list to be safe

        # Testing and interactive development
        "pytest"
        "isort"
        "pytest-cov"
        "ipython"
        "coverage"

        # Essential build tools
        "setuptools"
      ];

      pythonEnv = pythonOverridden.withPackages (
        ps:
          (map (name: ps.${name}) nixpkgspythondepnames)
          ++ [ps.adbutils ps.pyairtable ps.uiautomator2]
      );
    in {
      devShells.default = pkgs.mkShell {
        packages = [
          pythonEnv
          pkgs.android-tools
        ];

        shellHook = ''
          echo "---------------------------------------------------------------------"
          echo "nix dev shell ready for IGLoginAgent. (V2 - Corrected)"
          echo "Python environment (3.13) is active with all dependencies."
          echo "  python: $(which python) ($($(which python) --version 2>&1))"
          echo ""
          echo "This is a minimal environment for the Login and Warmup bots."
          echo "---------------------------------------------------------------------"
        '';
      };
    });
}
