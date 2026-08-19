using System;
using System.IO;
using System.Text;
using System.Threading;

namespace IM.Logging
{
    /// <summary>
    /// LotBoundary 단계 로그. 기존 WISVision 날짜 폴더에 txt 를 남기고, LAST 는 루트에 둔다.
    ///
    /// 출력 경로
    ///   C:\WISVision\Log\LotBoundary_LAST.txt
    ///   C:\WISVision\Log\{날짜}\LotBoundary_{날짜}.txt
    ///
    /// {날짜} 폴더는 새로 만들지 않고, 이미 있는 WISVision 날짜 폴더를 그대로 쓴다.
    /// (yyyyMMdd / yyyy-MM-dd / yyyy_MM_dd 중 오늘 폴더가 있으면 그걸 사용)
    /// 오늘 폴더가 아직 없으면 yyyyMMdd 로 생성한다. 이미 있으면 CreateDirectory 는 no-op.
    ///
    /// 출력 기준
    ///   BeginLot(lotId)  : Lot 시작 때 1줄. LAST 를 현재 Lot 으로 초기화.
    ///   Write(message)   : 단계마다 1줄. LAST+날짜 txt 둘 다 즉시 Flush(true).
    ///   EndLot(lot, res) : Lot 종료 때 1줄.
    ///   한 줄 형식       : [yyyy-MM-dd HH:mm:ss.fff] 메시지
    ///   LAST             : 현재 Lot 만 (다음 BeginLot 때 비움)
    ///   날짜 txt         : 그날 모든 Lot append
    ///
    /// 기존 코드 수정
    ///   1) 이 파일을 IM 프로젝트에 추가
    ///   2) 어제 넣은 LotBoundary 로그(날짜 폴더 LAST, AppendAllText 만 하는 코드) 삭제
    ///   3) Lot 시작/단계/종료에 BeginLot / Write / EndLot 호출
    /// </summary>
    public static class LotBoundaryLogger
    {
        public const string LastFileName = "LotBoundary_LAST.txt";
        public const string DateFormat = "yyyyMMdd";

        static readonly string[] DateFormats = new string[]
        {
            "yyyyMMdd",
            "yyyy-MM-dd",
            "yyyy_MM_dd"
        };

        public static string LogRoot = @"C:\WISVision\Log";

        static readonly object Gate = new object();
        static readonly UTF8Encoding Utf8NoBom = new UTF8Encoding(false);
        static readonly StringBuilder CurrentLot = new StringBuilder();

        public static string LastPath
        {
            get { return Path.Combine(LogRoot, LastFileName); }
        }

        /// <summary>
        /// 오늘 WISVision 이 이미 만든 날짜 폴더 이름을 쓴다.
        /// 없으면 yyyyMMdd.
        /// </summary>
        public static string DateStamp(DateTime now)
        {
            int i;
            for (i = 0; i < DateFormats.Length; i++)
            {
                string stamp = now.ToString(DateFormats[i]);
                if (Directory.Exists(Path.Combine(LogRoot, stamp)))
                {
                    return stamp;
                }
            }
            return now.ToString(DateFormat);
        }

        public static string DailyDirectory(DateTime now)
        {
            return Path.Combine(LogRoot, DateStamp(now));
        }

        public static string DailyPath(DateTime now)
        {
            string date = DateStamp(now);
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
