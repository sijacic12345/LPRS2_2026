// TEST KOD ZA PIN 9 (Bez servo biblioteke)
const int trigPin = A3;
const int echoPin = 9; // Tvoja fizicka lokacija

void setup() {
  Serial.begin(115200); 
  
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  
  Serial.println("--- TEST SENZORA NA PINU 9 ---");
}

void loop() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Merimo trajanje impulsa na pinu 9
  long duration = pulseIn(echoPin, HIGH, 30000);
  float distance = duration * 0.034 / 2;

  if (duration == 0) {
    Serial.println("GRESKA: Nema signala na pinu 9! Proveri kontakt.");
  } else {
    Serial.print("Distanca: ");
    Serial.print(distance);
    Serial.println(" cm");
  }

  delay(200);
}
