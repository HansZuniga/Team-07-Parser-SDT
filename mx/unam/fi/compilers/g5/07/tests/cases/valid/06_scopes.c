int main() {
    int x = 1;
    {
        float x = 2.5;
        x = x * 2.0;
    }
    {
        int y = x;
        {
            y = y + x;
        }
    }
    return x;
}
