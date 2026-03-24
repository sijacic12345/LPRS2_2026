#include <Servo.h>
#include "avr_io_bitfields.h"

#ifndef LED_BUILTIN
#define LED_BUILTIN 13
#endif

//////////////////
const int trigPin= A3;
const int echoPin= 9;

const int trigPin1 = A4;
const int echoPin1 = A5;

const int trigPin2 = 6;
const int echoPin2 = 7;

float duration, distance;
float duration2, distance2;
float duration1, distance1;

#define PG 2       // INT2
#define PWM 3      // OC2B
#define DIR 4

//pinovi tastera za skretanje i ubrzavanje

#define BTN_SERVO_L 12       // skretanje levo (servo)
#define BTN_SERVO_R A0      // skretanje desno (servo)
#define BTN_DEC A1          // smanjenje brzine BLDC
#define BTN_INC A2          // povecanje brzine BLDC

#define LED_DEBUG LED_BUILTIN
#define SERVO_PIN 8

//step i pocetna brzina//////////////////////////////////////////////////////////////////////

#define EFF_STEP 10
#define EFF_START 10

//step i granice ugla////////////////////////////////////////////////////////////////////////

#define SERVO_STEP 10
#define SERVO_MIN_ANGLE 0
#define SERVO_MAX_ANGLE 180

//definicija novog tipa//////////////////////////////////////////////////////////////////////
//32-bitni celi broj 
typedef i32 pulses_t;

//static - ogranicava vrednost promenljive na trenutni fajl
//volatile - vrednost se moze menjati van kontrole programa, da kompajler ne optimizuje pristup toj promenljivoj
//kompajler ce uvek ucitati vrednost iz RAM-a a ne iz cachea
static volatile pulses_t pos = 0;

//definicija novog tipa//////////////////////////////////////////////////////////////////////
enum dir_t {
  CW = +1,      //clockwise
  CCW = -1      //counter-clockwise
};
static volatile dir_t dir = CW;

//funkcija za promenu brzine ///////////////////////////////////////////////////////////////
//u8 osmobitni unsigned broj

static void set_abs_eff(u8 percents) {
  tc2.r.ocrb = percents;
}

//funkcija za promenu smera okretanja/////////////////////////////////////////////////////////////
static void set_dir(dir_t d) {
  dir = d;
  digitalWrite(DIR, dir == CW);
}
static void pos_pulse() {
  pos++;
}

//funkcija koja kontrolise promenu brzine i smer obrtanja//////////////////////////////////
static void set_eff(i8 eff) {
  if(eff > 0){
    set_dir(CW);
    set_abs_eff(eff);
  }else{
    set_dir(CCW);
    set_abs_eff(-eff);
  }
}

///////////////////////////////////////////////////////////////////////////////

ISR(TIMER2_COMPA_vect) {}

static i8 eff = EFF_START;

Servo servo;
static int servo_angle = 90; // centar
 

bool sensor_active = false;

void setup() {
  Serial.begin(115200); //senzor
  
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  
  pinMode(trigPin1, OUTPUT);
  pinMode(echoPin1, INPUT);

  pinMode(trigPin2, OUTPUT);
  pinMode(echoPin2, INPUT);

  pinMode(LED_DEBUG, OUTPUT);
  digitalWrite(LED_DEBUG, 0);

  pinMode(BTN_SERVO_L, INPUT_PULLUP);
  pinMode(BTN_SERVO_R, INPUT_PULLUP);
  pinMode(BTN_DEC, INPUT_PULLUP);
  pinMode(BTN_INC, INPUT_PULLUP);


 attachInterrupt(digitalPinToInterrupt(PG), pos_pulse, RISING);

  pinMode(DIR, OUTPUT);
  set_dir(CW);

  pinMode(PWM, OUTPUT);
  digitalWrite(PWM, 1);
  tc2.r.tccra = 0;
  tc2.r.tccrb = 0;
  irq.timsk[2] = 0;
  tc2.f.comb = 0b11;
  tc2.r.ocrb = 0;
  tc2.r.ocra = 100;
  tc2.f.wgm0 = 1;
  tc2.f.wgm1 = 0;
  tc2.f.wgm2 = 1;
  tc2.f.cs = 0b010;
  irq.timsk2.ociea = 1;

  set_eff(eff);

  servo.attach(SERVO_PIN);
  servo.write(servo_angle);
}

typedef unsigned long millis_t;

void loop() {

// prate prethodno stanje svakok tastera - na pocetku ni jedan nije pritisnut
// moraju biti static jer se inicijalizuju samo pri prvom prolasku kroz petlju 

  static bool prev_inc = false;
  static bool prev_dec = false;
  static bool prev_servo_l = false;
  static bool prev_servo_r = false;

// citanje trenutnog stanja tastera - jer su pull-up digitalRead vrati LOW kada su pritisnuti

  bool curr_inc = !digitalRead(BTN_INC);
  bool curr_dec = !digitalRead(BTN_DEC);
  bool curr_servo_l = !digitalRead(BTN_SERVO_L);
  bool curr_servo_r = !digitalRead(BTN_SERVO_R);

//detekcija rising-edge - true ako je taster sada pritisnut i prethodno nije bio

  bool re_inc = curr_inc && !prev_inc;
  bool re_dec = curr_dec && !prev_dec;
  bool re_servo_l = curr_servo_l && !prev_servo_l;
  bool re_servo_r = curr_servo_r && !prev_servo_r;


////////// NAPRED /////////////////////////////////////////////////////////////////////////////
  digitalWrite(trigPin, LOW); //senzor0
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  duration= pulseIn(echoPin, HIGH);
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

////////// DESNO /////////////////////////////////////////////////////////////////////////////

  digitalWrite(trigPin1, LOW); //senzor1
  delayMicroseconds(2);
  digitalWrite(trigPin1, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin1, LOW);

  duration1 = pulseIn(echoPin1, HIGH);
  distance1 = (duration1*.0343)/2;    //distanca u centimetrima
  delay(100);

  Serial.print("DESNO: ");
  Serial.println(distance1);

  if(distance1<8 ){
    eff = 0;
    Serial.println("STOP");
    set_eff(eff);
    sensor_active=true;
  }
  else{
    sensor_active=false;
  }

  delay(40);

////////// LEVO /////////////////////////////////////////////////////////////////////////////

  digitalWrite(trigPin2, LOW); //senzor2
  delayMicroseconds(2);
  digitalWrite(trigPin2, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin2, LOW);

  duration2 = pulseIn(echoPin2, HIGH);
  distance2 = (duration2*.0343)/2;    //distanca u centimetrima

  Serial.print("LEVO: ");
  Serial.println(distance2);

  if(distance2<8 ){
    eff = 0;
    Serial.println("STOP");
    set_eff(eff);
    sensor_active=true;
  }
  else{
    sensor_active=false;
  }

  delay(40);

///////////////////////////////////////////////////////////////////////////////////////////////////

//ako je aktiviran taster za povecanje/smanjenje brzine, poziva se funcija koja menja brzinu
//brzina se povecava za EFF_STEP ukoliko je to moguce unutar intervala -100, 100

  if(re_inc){
    eff = min(eff + EFF_STEP, 100);
  } else if(re_dec){
    eff = max(eff - EFF_STEP, -100);
  }
  set_eff(eff);

//ako je aktiviran taster za skretanje levo/desno, poziva se funkcija za promenu ugla
  if(re_servo_l){
    servo_angle = max(servo_angle - SERVO_STEP, SERVO_MIN_ANGLE);
    servo.write(servo_angle);
  } else if(re_servo_r){
    servo_angle = min(servo_angle + SERVO_STEP, SERVO_MAX_ANGLE);
    servo.write(servo_angle);
  }

  digitalWrite(LED_DEBUG, eff != 0);

  prev_inc = curr_inc;
  prev_dec = curr_dec;
  prev_servo_l = curr_servo_l;
  prev_servo_r = curr_servo_r;

  delay(10); // debounce

  static millis_t prev_t;
  static pulses_t prev_pos;
  pulses_t curr_pos = pos;
  millis_t curr_t = millis();

  pulses_t dp = curr_pos - prev_pos;
  millis_t dt = curr_t - prev_t;

  
  Serial.print(pos);
  Serial.print(" cnt\t");
  Serial.print("Servo: ");
  Serial.print(servo_angle);
  Serial.println(" deg");

  prev_pos = curr_pos;
  prev_t = curr_t;
}
