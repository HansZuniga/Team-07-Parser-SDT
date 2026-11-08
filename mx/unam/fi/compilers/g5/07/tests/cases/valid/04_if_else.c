int main() {
    int a = 1;
    if (a > 0) a = 2;
    if (a > 1) {
        a = 3;
    } else {
        a = 4;
    }
    if (a) if (a > 2) a = 5; else a = 6;
    return a;
}
