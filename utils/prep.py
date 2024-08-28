import os
import re
from io import StringIO

import numpy as np
import pandas as pd

def get_info_df(info_text):
    # 1) Aufteilung des Inhalts auf Key-List (Value) Paare
    raw_info_dict = key_entry_split(info_text)
    info_dict = entries_split(raw_info_dict)

    # 2) Allgemeine Bestimmung der Zeilen
    series_numb = len(info_dict["SAMPLE"])  # alternativ über IDENTITY

    # 3) Ausschluss der Keys mit wenig keys als series_numb
    key_value_count = count_entries_pro_key(info_dict)
    excluded_keys = [key for key, value in key_value_count.items() if value != series_numb]

    # 4) Dataframe bilden
    info_df = dict_to_dataframe(info_dict, ignore_keys=excluded_keys)

    # 5 Dataframe auf das Relevante (die wo mehr als 1 unique-Wert haben)
    unique_counts = info_df.nunique()
    series_relevant_columns = unique_counts[unique_counts > 1]
    info_df = info_df[series_relevant_columns.index.tolist()]

    # 6 Anpassung der Spaltennamen
    info_df.columns = info_df.columns.str.lower()
    info_df = info_df.rename(columns=replace_slash)

    # Konvertiere 'sample mass_mg' zu numerischen Werten, ignoriere Fehler
    info_df['sample mass_mg'] = pd.to_numeric(info_df['sample mass_mg'], errors='coerce')

    return info_df
    

def get_measurement_df(measurements_text, info_df):
    # Dataframe
    measurements_df = pd.read_csv(StringIO(measurements_text), sep=';', index_col=0)

    dsc_type = "unknown"
    if "mW/mg" in measurements_df.columns[0]:
        dsc_type = "mW/mg"
    elif "mW" in measurements_df.columns[0]:
        dsc_type = "mW"

    # 1) Anpassung der Spaltennamen
    num_cols = len(info_df)
    new_columns = [info_df.at[i, 'sample'] + '_' + info_df.at[i, 'segment'] for i in range(num_cols)]
    new_columns = [col.replace("/5", "") for col in new_columns]
    measurements_df.columns = new_columns

    # 2) Entfernung des Rauschens (Anfangs- und End-Werte)

    # ersten und letzten 25 Abschneiden
    measurements_df = measurements_df.iloc[25:-25]

    # 3) Entfernung des Initialisierungssegments (S1)
    columns_s1 = measurements_df.filter(like='_S1').columns

    measurements_df.drop(columns=columns_s1, inplace=True)

    # 4) Anpassung der Werte in mW

    measurements_df = measurements_df.apply(pd.to_numeric, errors='coerce')

    try:
        if dsc_type == "mW/mg":
            for column in measurements_df.columns:
                sample, _ = column.split('_')  # Sample und Segment ID extrahieren
                mass_mg_value = info_df.loc[info_df["sample"] == sample, "sample mass_mg"].iloc[0]
                measurements_df.loc[:, column] *= mass_mg_value
            dsc_type = "mW"

    except Exception as e:
        print(f"Error: {e}")


    return measurements_df

# Information Dataframe - Subfunktionen ------------------------------------------
# 1a) Einfache Key-Value Paare ----------------------------------
def key_entry_split(text):
    data = {}
    sections = text.strip().split("#")
    sections = sections[1:]  # erstes Element wird entfernt da leer (# ist am Anfang)
    for section in sections:
        key = section.split(":")[0]
        value_string = section.split(":")[1]
        data[key] = value_string.strip()
    return data


# 1b) Key-List Paare --------------------------------------------
# Aufteilung der Value-Strings in Value-Listen
def single_entry_split(text):
    return re.split(r'\s{2,}', text.strip())  # 2 oder mehrere Leerzeichen hintereinander


def entries_split(data):
    result = {}
    for key, value in data.items():
        result[key] = single_entry_split(value)
    return result


# 3) -------------------------------------------------------------
def count_entries_pro_key(dictionary):
    result = {}
    for key, values in dictionary.items():
        anzahl_der_values = len(values)
        result[key] = anzahl_der_values
    return result


# 4) Dataframe ---------------------------------------------------
def dict_to_dataframe(dictionary, ignore_keys=None):
    if ignore_keys is None:
        ignore_keys = []
    # Filtern der Schlüssel, die ignoriert werden sollen
    filtered_dict = {key: values for key, values in dictionary.items() if key not in ignore_keys}
    return pd.DataFrame(filtered_dict)


# Hilfsfunktionen ----------------------------------------------------

def replace_slash(column_name):
    return re.sub(r'\s*/\s*', '_', column_name.lower())
    