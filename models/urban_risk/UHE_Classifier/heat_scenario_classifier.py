# Heat Risk Classification Module (heat_scenario_classifier.py):
# Reuses the preprocessing and classification logic from the previous code.
# Calculates the Heat Index and assigns scenarios ('Low', 'Moderate', 'High') based on thresholds.
# Trains a Random Forest Classifier and provides a function to predict scenarios for new inputs.

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

def load_and_preprocess_data(file_path):
    # Load dataset and impute missing values with mean for numerical columns
    data = pd.read_csv(file_path)
    for col in data.columns:
        if data[col].dtype != 'object':
            data[col].fillna(data[col].mean(), inplace=True)
    
    # Convert avg_temp to Fahrenheit and calculate Heat Index
    data['avg_temp_f'] = data['avg_temp'] * 9/5 + 32
    data['heat_index'] = (
        -42.379 + 2.04901523 * data['avg_temp_f'] + 10.14333127 * data['avg_humidity']
        - 0.22475541 * data['avg_temp_f'] * data['avg_humidity']
        - 0.00683783 * data['avg_temp_f']**2 - 0.05481717 * data['avg_humidity']**2
        + 0.00122874 * data['avg_temp_f']**2 * data['avg_humidity']
        + 0.00085282 * data['avg_temp_f'] * data['avg_humidity']**2
        - 0.00000199 * data['avg_temp_f']**2 * data['avg_humidity']**2
    )
    
    # Assign scenarios based on Heat Index and merge 'Extreme' with 'High'
    data['scenario'] = data['heat_index'].apply(
        lambda hi: 'Low' if hi < 80 else 'Moderate' if hi < 90 else 'High'
    )
    return data

def train_classifier(data, features):
    # Select features and target, then split and scale data
    X = data[features]
    y = data['scenario']
    X_train, _, y_train, _ = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    # Train Random Forest Classifier
    rf_classifier = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    rf_classifier.fit(X_train_scaled, y_train)
    return scaler, rf_classifier

def predict_scenario(input_data, scaler, model, feature_names):
    # Predict scenario for new input data
    input_df = pd.DataFrame([input_data], columns=feature_names)
    input_scaled = scaler.transform(input_df)
    prediction = model.predict(input_scaled)
    return prediction[0]