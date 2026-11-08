int main() {
    int i = 0;
    int j;
    while (i < 10) i = i + 1;
    while (i > 0) {
        j = 0;
        while (j < i) {
            j = j + 1;
        }
        i = i - 1;
    }
    return i;
}
