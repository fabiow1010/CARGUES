### Cargue de datos ZHG_U

### para cimitarra "xtf_final_cimitarra"."vm_zonahomogeneageoeconomicaurbana"
### para sabana "pruebas_xtf_sabana_torres"."vm_zonahomogeneageoeconomicaurbana"
### para puerto "xtf_final_puerto_wilches"."vm_zonahomogeneageoeconomicaurbana"


import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
CAPA = "vm_zonahomogeneafisicaurbana"
MPIO = "pruebas_xtf_sabana_torres"
ARCHIVO_CSV = f"{CAPA}.csv"


def crear_conexion():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=5432
    )


def ejecutar_cargue():
    conexion = None
    try:
        # Leer CSV
        df = pd.read_csv(ARCHIVO_CSV)

        if set(df.columns) != {"WKT", "t_id"}:
            raise ValueError("El CSV debe tener las columnas WKT y t_id.")

        if df.empty or df[["WKT", "t_id"]].isna().any().any():
            raise ValueError("El CSV contiene datos vacíos.")

        if df["t_id"].duplicated().any():
            raise ValueError("Existen t_id duplicados en el CSV.")

        conexion = crear_conexion()

        print(f"Conexión establecida. Registros: {len(df)}")

        with conexion.cursor() as cursor:

            for fila in df.itertuples(index=False):

                cursor.execute("""
                    UPDATE """ + MPIO + """.""" + CAPA + """
                    SET geometria = ST_GeomFromText(
                        %s, ST_SRID(geometria)
                    )
                    WHERE t_id = %s
                      AND geometria IS NOT NULL
                    RETURNING
                        t_id,
                        ST_IsValid(geometria),
                        ST_IsEmpty(geometria),
                        ST_IsValidReason(geometria);
                """, (fila.WKT, fila.t_id))

                resultados = cursor.fetchall()

                if len(resultados) != 1:
                    raise ValueError(
                        f"t_id {fila.t_id}: se esperaba un registro "
                        f"y se encontraron {len(resultados)}."
                    )

                _, valida, vacia, motivo = resultados[0]

                if not valida or vacia:
                    raise ValueError(
                        f"Geometría inválida en t_id {fila.t_id}: {motivo}"
                    )

        conexion.commit()
        
        print(F"COMMIT exitoso. Registros actualizados en la capa {CAPA} del município {MPIO}: {len(df)}")

        print(f"COMMIT exitoso. Registros actualizados: {len(df)}")

    except Exception as error:

        if conexion:
            conexion.rollback()

        print(f"ERROR: {error}")
        print("ROLLBACK ejecutado. No se guardaron los cambios.")

    finally:

        if conexion:
            conexion.close()
            print("Conexión cerrada.")


if __name__ == "__main__":
    ejecutar_cargue()
