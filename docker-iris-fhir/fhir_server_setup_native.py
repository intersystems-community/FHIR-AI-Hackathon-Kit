import iris


HOST = "localhost"
PORT = 32782
USER = "superuser"
PASSWORD = "SYS"


def connect(namespace):
    conn = iris.createConnection(HOST, PORT, namespace, USER, PASSWORD)
    return conn, iris.createIRIS(conn)


class FHIRServerSetup:
    def __init__(self, namespace: str, endpoint: str, datapath: str = "/home/irisowner/dev/data/fhir"):
        self.FHIR_NAMESPACE = namespace
        self.FHIR_ENDPOINT = endpoint
        self.DATAPATH = datapath

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

            strategy_class = "HS.FHIRServer.Storage.Json.InteractionsStrategy"
            metadata = "hl7.fhir.r4.core@4.0.1"

            irispy.classMethodVoid("HS.FHIRServer.Installer", "InstallNamespace")
            irispy.classMethodVoid("HS.FHIRServer.Installer", "InstallInstance", self.FHIR_ENDPOINT, strategy_class, metadata)
        finally:
            conn.close()

    def load_fhir_data(self):
        conn, irispy = connect(self.FHIR_NAMESPACE)
        try:
            irispy.classMethodVoid(
                "HS.FHIRServer.Tools.DataLoader",
                "SubmitResourceFiles",
                self.DATAPATH, "FHIRServer", self.FHIR_ENDPOINT, 1, "^fhirlogs"
            )
        finally:
            conn.close()


if __name__ == "__main__":
    fhir_setup = FHIRServerSetup("FHIRSERVER", "/fhir/r4", "/tmp/fhir")
    fhir_setup.install()
