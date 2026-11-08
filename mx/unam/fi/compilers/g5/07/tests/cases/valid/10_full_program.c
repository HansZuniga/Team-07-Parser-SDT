int main() {
    int n = 10;
    int suma = 0;
    int i = 1;
    float promedio;
    char letra = 'p';
    while (i <= n) {
        if (i % 2 == 0) {
            suma = suma + i;
        } else {
            suma = suma - 1;
        }
        i = i + 1;
    }
    promedio = suma / 5.0;
    if (promedio > 3.5) letra = 'a';
    return suma;
}
