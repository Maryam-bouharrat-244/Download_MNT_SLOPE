# Configuration pour l'application MNT France Generator

# Chemins
CSV_DEPARTMENTS = r"C:\Users\marya\Downloads\projet test\deps.csv"
OUTPUT_DIR = r"C:\Users\marya\Downloads"
WORK_DIR = r"C:\Users\marya\Downloads\mnt_work"

# Configuration de téléchargement
TIMEOUT_DOWNLOAD = 300  # secondes (5 minutes)
CHUNK_SIZE = 8192  # bytes
MAX_RETRIES = 3

# Configuration d'extraction
CLEAR_TMP_AFTER_VRT = False  # Garder les fichiers ASC après génération VRT

# Configuration Streamlit
STREAMLIT_SERVER_PORT = 8501
STREAMLIT_LOGGER_LEVEL = "info"
STREAMLIT_CLIENT_SHOW_ERROR_DETAILS = True

# Projection (Lambert93 - IGN69)
SRS_DEFINITION = """PROJCS["Lambert93",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic_2SP"],PARAMETER["standard_parallel_1",49],PARAMETER["standard_parallel_2",44],PARAMETER["latitude_of_origin",46.5],PARAMETER["central_meridian",3],PARAMETER["false_easting",700000],PARAMETER["false_northing",6600000],UNIT["Meter",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","2154"]]"""

# Paramètres MNT
MNT_NODATA_VALUE = -9999
MNT_DATA_TYPE = "Float32"
MNT_CELLSIZE = 5.0  # mètres

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = None  # None = console only, ou chemin vers fichier
