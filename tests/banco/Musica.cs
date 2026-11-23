// Finta musica/video nel browser: ogni 10 ms deve preparare un pezzetto di audio (1,5 ms di lavoro).
// Se arriva in ritardo di piu' di 10 ms rispetto alla scadenza, l'audio "gratta": conta quante volte succede.
using System; using System.Diagnostics; using System.IO; using System.Threading;
public static class Musica {
  public static void Main(string[] a) {
    string outp = a[0]; var sw = Stopwatch.StartNew(); double target = 0; double x = 1; long glitch = 0, n = 0; double worst = 0;
    while (true) {
      target += 10;
      var t0 = sw.Elapsed.TotalMilliseconds; while (sw.Elapsed.TotalMilliseconds - t0 < 1.5) { x = x * 1.0000001 + Math.Sqrt(x); if (x > 1e9) x = 1; }
      double now = sw.Elapsed.TotalMilliseconds; double late = now - target; n++;
      if (late > 10) glitch++; if (late > worst) worst = late;
      if (late > 0) target = now;  // in ritardo: riparte da adesso (come un buffer audio che ha perso un pezzo)
      else while (sw.Elapsed.TotalMilliseconds < target) Thread.Sleep(1);
      if (n % 100 == 0) File.WriteAllText(outp, n + " " + glitch + " " + worst.ToString("F1", System.Globalization.CultureInfo.InvariantCulture));
    }
  }
}
