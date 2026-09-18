import iris
import os
import shutil
from pathlib import Path

def zn(namespace):
    iris.execute(f'zn "{namespace}"')


def unexpire_passwords():
    # FOR DEV ONLY - DO NOT USE IN PRODUCTION
    zn("%SYS")
    print("Unexpiring passwords")
    iris.Security.Users.UnExpireUserPasswords("*")




class FHIRServerSetup():
    def __init__(self, namespace: str, endpoint: str, datapath: str = "/home/irisowner/dev/data/fhir"):
        self.FHIR_NAMESPACE = namespace
        self.FHIR_ENDPOINT = endpoint
        self.DATAPATH = datapath

    def install(self, overwrite=False):
        self.create_fhir_server(overwrite=overwrite)
        self.load_fhir_data()

    def create_fhir_server(self, overwrite=False):
        zn("HSLIB")

        if not iris._SYS.Namespace.Exists(self.FHIR_NAMESPACE):
            iris.HS.Util.Installer.Foundation.Install(self.FHIR_NAMESPACE)

        zn(self.FHIR_NAMESPACE)

        exists = iris.HS.FHIRServer.ServiceInstance.ExistsByUrl(self.FHIR_ENDPOINT)

        if exists and not overwrite:
            print("FHIR server already exists, skipping...")
            return 1

        if exists and overwrite:
            print("FHIR server exists, overwriting...")
            iris.HS.FHIRServer.Installer.UninstallInstance(self.FHIR_ENDPOINT)

        strategy_class = "HS.FHIRServer.Storage.Json.InteractionsStrategy"
        metadata = "hl7.fhir.r4.core@4.0.1"

        iris.HS.FHIRServer.Installer.InstallNamespace()
        iris.HS.FHIRServer.Installer.InstallInstance(self.FHIR_ENDPOINT, strategy_class, metadata)

    def load_fhir_data(self):
        zn(self.FHIR_NAMESPACE)
        iris.HS.FHIRServer.Tools.DataLoader.SubmitResourceFiles(
            self.DATAPATH, "FHIRServer", self.FHIR_ENDPOINT, 1, "^fhirlogs"
        )




def setup_swagger_app(src="/home/irisowner/dev/src/swagger-ui", dest="/opt/fhir/swagger-ui"):

    destination = Path(dest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, destination, dirs_exist_ok=True)
    print(f"Copied {src} to {dest}")

    zn("%SYS")
    props_ref = iris.ref(None)
    sc_ref = iris.ref(None)
    exists = iris.Security.Applications.Exists("/fhir/swagger-ui", props_ref, sc_ref)
    if not exists:
        prop = iris.arrayref({
            "Type": 2,
            "NameSpace": "USER",
            "Path": dest,
            "ServeFiles": 1,
            "ServeFilesTimeout": 3600,
            "AutheEnabled": 64,
            "Enabled": 1,
        })
        sc = iris.Security.Applications.Create("/fhir/swagger-ui", prop)
        if not iris.system.Status.IsOK(sc):
            raise RuntimeError(iris.system.Status.GetErrorText(sc))
        print("Created /fhir/swagger-ui application")
    else:
        print("/fhir/swagger-ui application already exists, skipping...")
    zn("USER")


if __name__ == "__main__":
    unexpire_passwords()
    fhir_setup = FHIRServerSetup("FHIRSERVER", "/fhir/r4", "/opt/fhir/data")
    fhir_setup.install()
    setup_swagger_app()
