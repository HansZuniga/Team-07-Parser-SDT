int main() {
    int a = 7;
    int b = 2;
    float f = 1.5;
    int r;
    r = a + b * 3 - (a - b) / 2;
    r = a % b + -a;
    r = !(a == b) + (a != b);
    r = (a < b) + (a <= b) + (a > b) + (a >= b);
    f = f * a + b / 2.0;
    return r;
}
