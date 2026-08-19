using System;
using System.IO;
using System.Text;
using System.Threading;

namespace IM.Logging
{
    /// <summary>
    /// LotBoundary 단계 로그를 디스크까지 즉시 Flush 한다.
    ///
    /// C:\WISVision\Log\LotBoundary_LAST.txt          ← 현재 Lot (루트, 날짜 폴더 아님)
    /// C:\WISVision\Log\{yyyyMMdd}\LotBoundary_{yyyyMMdd}.txt
    ///
    /// LAST 가 안 보이던 흔한 원인
    /// 1) LAST 를 날짜 폴더 안에 씀 (루트가 아니라 Log\20260819\LotBoundary_LAST.txt)
    /// 2) StreamWriter 를 Lot 시작 때 열고, 끝날 때까지 Flush 안 함 → 파일 0바이트
    /// 3) Flush() 만 호출하고 FileStream.Flush(true) 를 안 함 → OS 캐시에만 남음
    /// 4) 공유 잠금(FileShare.None) 때문에 실행 중엔 파일을 못 염
    /// </summary>
    public static class LotBoundaryLogger
    {
        public const string LastFileName = "LotBoundary_LAST.txt";
        public const string DateFormat = "yyyyMMdd";

        public static string LogRoot = @"C:\WISVision\Log";

        static readonly object Gate = new object();
        static readonly UTF8Encoding Utf8NoBom = new UTF8Encoding(false);
        static readonly StringBuilder CurrentLot = new StringBuilder();

        public static string LastPath
        {
            get { return Path.Combine(LogRoot, LastFileName); }
        }

        public static string DailyDirectory(DateTime now)
        {
            return Path.Combine(LogRoot, now.ToString(DateFormat));
        }

        public static string DailyPath(DateTime now)
        {
            string date = now.ToString(DateFormat);
            return Path.Combine(DailyDirectory(now), "LotBoundary_" + date + ".txt");
        }

        /// <summary>새 Lot 시작. LAST 를 비우고 헤더를 즉시 기록한다.</summary>
        public static void BeginLot(string lotId)
        {
            lock (Gate)
            {
                CurrentLot.Length = 0;
                WriteUnlocked("=== LotBoundary START lot=" + NullToEmpty(lotId) + " ===");
            }
        }

        public static void EndLot(string lotId, string result)
        {
            Write("=== LotBoundary END lot=" + NullToEmpty(lotId) + " result=" + NullToEmpty(result) + " ===");
        }

        /// <summary>단계 한 줄을 daily append + LAST 전체 재기록 후 디스크 Flush.</summary>
        public static void Write(string message)
        {
            lock (Gate)
            {
                WriteUnlocked(message);
            }
        }

        static void WriteUnlocked(string message)
        {
            DateTime now = DateTime.Now;
            string line = "[" + now.ToString("yyyy-MM-dd HH:mm:ss.fff") + "] " + NullToEmpty(message)
                          + Environment.NewLine;

            CurrentLot.Append(line);

            Directory.CreateDirectory(LogRoot);
            Directory.CreateDirectory(DailyDirectory(now));

            // daily: append
            AppendAndFlushToDisk(DailyPath(now), line, true);

            // LAST: 항상 Log 루트에 현재 Lot 전체를 덮어쓴다 (날짜 폴더에 쓰지 말 것)
            RewriteAndFlushToDisk(LastPath, CurrentLot.ToString());
        }

        static void AppendAndFlushToDisk(string path, string text, bool createBomIfNew)
        {
            bool isNew = !File.Exists(path) || new FileInfo(path).Length == 0;
            FileMode mode = File.Exists(path) ? FileMode.Append : FileMode.Create;

            FileStream fs = null;
            StreamWriter sw = null;
            try
            {
                fs = new FileStream(path, mode, FileAccess.Write, FileShare.ReadWrite);
                sw = new StreamWriter(fs, Utf8NoBom);
                sw.AutoFlush = true;
                if (createBomIfNew && isNew && fs.Length == 0)
                {
                    byte[] bom = Encoding.UTF8.GetPreamble();
                    fs.Write(bom, 0, bom.Length);
                }
                sw.Write(text);
                sw.Flush();
                fs.Flush(true);
            }
            finally
            {
                if (sw != null) sw.Dispose();
                if (fs != null) fs.Dispose();
            }
        }

        static void RewriteAndFlushToDisk(string path, string content)
        {
            // temp → replace 로 0바이트 LAST 를 읽지 않게 한다.
            string tempPath = path + ".tmp";
            FileStream fs = null;
            try
            {
                fs = new FileStream(tempPath, FileMode.Create, FileAccess.Write, FileShare.Read);
                byte[] bom = Encoding.UTF8.GetPreamble();
                fs.Write(bom, 0, bom.Length);
                byte[] bytes = Utf8NoBom.GetBytes(content);
                fs.Write(bytes, 0, bytes.Length);
                fs.Flush(true);
            }
            finally
            {
                if (fs != null) fs.Dispose();
            }

            ReplaceFile(tempPath, path);
        }

        static void ReplaceFile(string source, string destination)
        {
            const int retry = 8;
            for (int i = 0; i < retry; i++)
            {
                try
                {
                    if (File.Exists(destination))
                    {
                        File.Copy(source, destination, true);
                        File.Delete(source);
                    }
                    else
                    {
                        File.Move(source, destination);
                    }
                    return;
                }
                catch (IOException)
                {
                    Thread.Sleep(20 * (i + 1));
                }
            }

            // 마지막 시도: 직접 덮어쓰기
            File.Copy(source, destination, true);
            try { File.Delete(source); } catch (IOException) { }
        }

        static string NullToEmpty(string value)
        {
            return value == null ? string.Empty : value;
        }
    }
}
