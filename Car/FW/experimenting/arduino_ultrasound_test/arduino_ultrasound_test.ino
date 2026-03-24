// TEST KOD (Bez servo biblioteke)

const int trigPin = A3; const int echoPin = 9; // Prednji
//const int trigPin = A4; const int echoPin = A5; // right
//const int trigPin = 6; const int echoPin = 7; // left

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
    Serial.println("GRESKA: Nema signala! Proveri kontakt.");
  } else {
    Serial.print("Distanca: ");
    Serial.print(distance);
    Serial.println(" cm");
  }

  delay(1000);
}
