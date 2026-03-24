const int trigPin= A3;
const int echoPin= 9;
float duration, distance;

void setup() {
    Serial.begin(115200); //senzor
    
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);

}

void loop(){
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    duration= pulseIn(echoPin, HIGH); //pulseIn meri trajanje elektricnog impulsa i vraca trajanje u ms
    distance= (duration*.0343)/2;    //distanca u centimetrima

    Serial.print("NAPRED: ");
    Serial.println(distance);

    if(distance<8 && distance!=0){
        eff = 0;
        Serial.println("STOP");
        set_eff(eff);
        sensor_active=true;
    }
    else{
        sensor_active=false;
    }

    delay(40);
}