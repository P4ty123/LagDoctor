// Finto gioco: ogni frame = lavoro del "thread principale" + lavoro diviso su tutti i core (come un job system).
// Misura il tempo di ogni frame e lo scrive in un file. Uso: FakeGame.exe <file.csv> <secondi> <riscaldamento>
using System; using System.Diagnostics; using System.IO; using System.Threading; using System.Threading.Tasks;
public static class FakeGame {
  static double Work(int n, double seed) { double x = seed; for (int i = 0; i < n; i++) { x = x * 1.0000001 + Math.Sqrt(i + x) * 0.5; if (x > 1e9) x = 1; } return x; }
  public static void Main(string[] a) {
    string outp = a[0]; double secs = double.Parse(a[1]), warm = double.Parse(a[2]);
    int cores = Environment.ProcessorCount; double sink = 0;
    var sw = Stopwatch.StartNew(); var frames = new System.Collections.Generic.List<double>();
    double last = 0;
    while (true) {
      sink += Work(150000, sink);                                   // logica di gioco (un solo thread)
      Parallel.For(0, cores, k => { Work(220000, k); });            // "rendering" e fisica su tutti i core
      double now = sw.Elapsed.TotalMilliseconds;
      if (now / 1000.0 > warm) frames.Add(now - last);
      last = now;
      if (now / 1000.0 > warm + secs) break;
    }
    File.WriteAllLines(outp, frames.ConvertAll(f => f.ToString("F3", System.Globalization.CultureInfo.InvariantCulture)));
    if (sink == 42) Console.WriteLine(sink);
  }
}
