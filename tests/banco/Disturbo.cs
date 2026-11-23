// Programma "in background" che usa un core al 100% (come un browser pesante, una conversione o un antivirus).
using System;
public static class Disturbo {
  public static void Main(string[] a) { double x = 1; long i = 0; while (true) { x = x * 1.0000001 + Math.Sqrt(i++ + x) * 0.5; if (x > 1e9) x = 1; } }
}
