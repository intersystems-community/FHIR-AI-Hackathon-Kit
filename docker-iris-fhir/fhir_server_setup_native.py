import base64
import urllib.request
from pathlib import Path

import iris


HOST = "localhost"
PORT = 1972
WEB_PORT = 52773
# Host-side copy of the bundles, POSTed to the FHIR endpoint
HTTP_DATA_DIR = Path(__file__).parent / "data" / "fhir"
USER = "superuser"
PASSWORD = "SYS"


def connect(namespace):
    conn = iris.createConnection(HOST, PORT, namespace, USER, PASSWORD)
    return conn, iris.createIRIS(conn)


class FHIRServerSetup:
    def __init__(self, namespace: str, endpoint: str):
        self.FHIR_NAMESPACE = namespace
        self.FHIR_ENDPOINT = endpoint

    def install(self, overwrite=False):
        self.create_fhir_server(overwrite=overwrite)
        self.load_fhir_data()

    def create_fhir_server(self, overwrite=False):
        conn, irispy = connect("HSLIB")
        try:
            ns_exists = irispy.classMethodBoolean("%SYS.Namespace", "Exists", self.FHIR_NAMESPACE)
            if not ns_exists:
                irispy.classMethodVoid("HS.Util.Installer.Foundation", "Install", self.FHIR_NAMESPACE)
        finally:
            conn.close()

        conn, irispy = connect(self.FHIR_NAMESPACE)
        try:
            exists = irispy.classMethodBoolean("HS.FHIRServer.ServiceInstance", "ExistsByUrl", self.FHIR_ENDPOINT)

            if exists and not overwrite:
                print("FHIR server already exists, skipping...")
                return

            if exists and overwrite:
                print("FHIR server exists, overwriting...")
                irispy.classMethodVoid("HS.FHIRServer.Installer", "UninstallInstance", self.FHIR_ENDPOINT)

            strategy_class = "HS.FHIRServer.Storage.JsonAdvSQL.InteractionsStrategy"
            metadata = "hl7.fhir.r4.core@4.0.1"

            irispy.classMethodVoid("HS.FHIRServer.Installer", "InstallNamespace")
            irispy.classMethodVoid("HS.FHIRServer.Installer", "InstallInstance", self.FHIR_ENDPOINT, strategy_class, metadata)
        finally:
            conn.close()

    def load_fhir_data(self):
        # Bundles sorted so hospital/practitioner info loads before patient bundles that reference them
        files = sorted(
            HTTP_DATA_DIR.glob("*.json"),
            key=lambda p: (not p.name.startswith(("hospitalInformation", "practitionerInformation")), p.name),
        )
        if not files:
            raise FileNotFoundError(f"No FHIR bundles found in {HTTP_DATA_DIR}")

        base_url = f"http://{HOST}:{WEB_PORT}{self.FHIR_ENDPOINT}"
        auth = base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
        for i, path in enumerate(files, 1):
            print(f"[{i}/{len(files)}] POST {path.name} -> {base_url}")
            req = urllib.request.Request(
                base_url,
                data=path.read_bytes(),
                method="POST",
                headers={
                    "Content-Type": "application/fhir+json",
                    "Accept": "application/fhir+json",
                    "Authorization": f"Basic {auth}",
                },
            )
            # urlopen raises HTTPError on 4xx/5xx; let it propagate
            with urllib.request.urlopen(req, timeout=600) as resp:
                print(f"    HTTP {resp.status}")


def setup_swagger_app(path="/opt/fhir/swagger-ui", name="/fhir/swagger-ui"):
    # path is a path inside the IRIS container; files must already be there (copy is not done over the native API)
    conn, irispy = connect("%SYS")
    try:
        app_ref = iris.IRISReference(None)
        sc_ref = iris.IRISReference(None)
        exists = irispy.classMethodBoolean("Security.Applications", "Exists", name, app_ref, sc_ref)
        if exists:
            print(f"{name} application already exists, skipping...")
            return

        props = {
            "Type": 2,
            "NameSpace": "USER",
            "Path": path,
            "ServeFiles": 1,
            "ServeFilesTimeout": 3600,
            "AutheEnabled": 64,
            "Enabled": 1,
        }
        # Create() takes a subscripted ByRef array, which IRISReference cannot express, so build the object and save it
        app = irispy.classMethodObject("Security.Applications", "%New")
        app.set("Name", name)
        for key, value in props.items():
            app.set(key, value)
        sc = app.invoke("%Save")
        if not irispy.classMethodBoolean("%SYSTEM.Status", "IsOK", sc):
            raise RuntimeError(irispy.classMethodString("%SYSTEM.Status", "GetErrorText", sc))
        print(f"Created {name} application")
    finally:
        conn.close()


if __name__ == "__main__":
    fhir_setup = FHIRServerSetup("FHIRSERVER", "/fhir/r4")
    fhir_setup.install()
    setup_swagger_app()
