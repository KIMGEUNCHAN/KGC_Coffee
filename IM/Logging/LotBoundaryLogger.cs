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
    /// 폴더는 직접 만들 필요 없다. Write/BeginLot 때 전부 자동 생성한다.
    ///   C:\WISVision\Log\
    ///   C:\WISVision\Log\{yyyyMMdd}\
    /// LAST/날짜 txt 파일도 첫 로그에서 자동 생성한다.
    ///
    /// LAST 가 안 보이던 흔한 원인
    /// 1) LAST 를 날짜 폴더 안에 씀 (루트가 아니라 Log\20260819\LotBoundary_LAST.txt)
    /// 2) 기존 WISVision 로그는 날짜 폴더에만 쓰고 LAST 파일을 안 만듦
    /// 3) StreamWriter 를 Lot 시작 때 열고, 끝날 때까지 Flush 안 함 → 파일 0바이트
    /// 4) Flush() 만 호출하고 FileStream.Flush(true) 를 안 함 → OS 캐시에만 남음
    /// 5) 공유 잠금(FileShare.None) 때문에 실행 중엔 파일을 못 염
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

        /// <summary>
        /// Log 루트와 오늘 날짜 폴더를 만든다. 이미 있으면 그냥 넘어간다.
        /// 앱 시작 때 호출하면 탐색기에 폴더가 미리 보인다.
        /// 날짜 폴더에만 LAST/LotBoundary 로그가 있으면 루트 LAST 로 복사한다.
        /// </summary>
        public static void EnsureDirectories()
        {
            Directory.CreateDirectory(LogRoot);
            Directory.CreateDirectory(DailyDirectory(DateTime.Now));
            RecoverLastFromDatedLogs();
        }

        /// <summary>
        /// 루트 LAST 가 없을 때 날짜 폴더 쪽 LotBoundary 로그를 루트로 끌어온다.
        /// WISVision 일반 로그는 있는데 LotBoundary_LAST 만 없는 경우를 맞춘다.
        /// </summary>
        public static bool RecoverLastFromDatedLogs()
        {
            if (File.Exists(LastPath))
            {
                return false;
            }

            Directory.CreateDirectory(LogRoot);

            string datedLastToday = Path.Combine(DailyDirectory(DateTime.Now), LastFileName);
            if (CopyIfExists(datedLastToday, LastPath))
            {
                return true;
            }

            if (CopyIfExists(DailyPath(DateTime.Now), LastPath))
            {
                return true;
            }

            if (!Directory.Exists(LogRoot))
            {
                return false;
            }

            string newest = FindNewestLotBoundaryFile();
            return CopyIfExists(newest, LastPath);
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

            EnsureDirectories();
            Directory.CreateDirectory(DailyDirectory(now));

            // LAST 를 먼저 루트에 쓴다. daily 만 되고 LAST 가 없는 상태를 막는다.
            RewriteAndFlushToDisk(LastPath, CurrentLot.ToString());

            // daily: append
            AppendAndFlushToDisk(DailyPath(now), line, true);
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

        static string FindNewestLotBoundaryFile()
        {
            string newest = null;
            DateTime newestTime = DateTime.MinValue;
            string[] dirs;
            try
            {
                dirs = Directory.GetDirectories(LogRoot);
            }
            catch (IOException)
            {
                return null;
            }

            int i;
            for (i = 0; i < dirs.Length; i++)
            {
                ConsiderFile(Path.Combine(dirs[i], LastFileName), ref newest, ref newestTime);
                string[] files;
                try
                {
                    files = Directory.GetFiles(dirs[i], "LotBoundary_*.txt");
                }
                catch (IOException)
                {
                    continue;
                }

                int j;
                for (j = 0; j < files.Length; j++)
                {
                    ConsiderFile(files[j], ref newest, ref newestTime);
                }
            }

            return newest;
        }

        static void ConsiderFile(string path, ref string newest, ref DateTime newestTime)
        {
            if (path == null || !File.Exists(path))
            {
                return;
            }
            if (string.Equals(Path.GetFullPath(path), Path.GetFullPath(LastPath), StringComparison.OrdinalIgnoreCase))
            {
                return;
            }

            DateTime t = File.GetLastWriteTime(path);
            if (newest == null || t > newestTime)
            {
                newest = path;
                newestTime = t;
            }
        }

        static bool CopyIfExists(string source, string destination)
        {
            if (source == null || !File.Exists(source))
            {
                return false;
            }

            File.Copy(source, destination, true);
            return true;
        }

        static string NullToEmpty(string value)
        {
            return value == null ? string.Empty : value;
        }
    }
}
