using System;
using System.IO;
using System.Text;
using System.Threading;

namespace IM.Logging
{
    /// <summary>
    /// AlignData.csv 에 Void Good/NG 를 남길 때 쓰는 안전한 쪽.
    ///
    /// 하지 말 것
    ///   FileMode.Create 로 AlignData 를 새로 만들기
    ///   GOOD/NG 를 새 행으로 Append
    ///   OffsetX/Y, Score, Align Result 칸을 Void 값으로 덮기
    ///
    /// 할 것
    ///   기존 행을 유지하고 맨 끝 열 VoidResult 만 갱신
    ///   값은 GOOD 또는 NG
    ///
    ///   AlignDataVoidLogger.WriteDieResult(path, "1", "NG");
    ///   AlignDataVoidLogger.WriteWaferResult(path, "GOOD");
    /// </summary>
    public static class AlignDataVoidLogger
    {
        public const string VoidColumn = "VoidResult";
        public const string Good = "GOOD";
        public const string Ng = "NG";

        static readonly object objLock = new object();

        public static string NormalizeJudge(string judge)
        {
            if (judge == null)
            {
                return "";
            }
            string str = judge.Trim().ToUpper();
            if (str == "OK" || str == "PASS" || str == "GOOD" || str == "G")
            {
                return Good;
            }
            if (str == "NG" || str == "FAIL" || str == "NOGOOD" || str == "N")
            {
                return Ng;
            }
            return str;
        }

        public static void WriteDieResult(string csvPath, string dieKey, string judge)
        {
            WriteDieResult(csvPath, dieKey, judge, 0);
        }

        /// <param name="keyColumnIndex">다이 키가 있는 열. 기본 0 (No). 헤더가 있으면 헤더 이름 No/Die/Index 도 찾는다.</param>
        public static void WriteDieResult(string csvPath, string dieKey, string judge, int keyColumnIndex)
        {
            if (csvPath == null || csvPath == "")
            {
                throw new ArgumentException("csvPath");
            }
            string strJudge = NormalizeJudge(judge);
            if (strJudge != Good && strJudge != Ng)
            {
                throw new ArgumentException("judge must be GOOD or NG");
            }
            if (dieKey == null)
            {
                dieKey = "";
            }

            lock (objLock)
            {
                CsvTable table = CsvTable.Load(csvPath);
                table.EnsureVoidColumn();
                int nKey = table.FindKeyColumn(keyColumnIndex);
                int nVoid = table.VoidColumnIndex();
                bool bHit = false;
                int i;
                for (i = 0; i < table.Rows.Length; i++)
                {
                    string[] arr = table.Rows[i];
                    if (arr.Length <= nKey)
                    {
                        continue;
                    }
                    if (string.Compare(arr[nKey].Trim(), dieKey.Trim(), true) == 0)
                    {
                        table.SetCell(i, nVoid, strJudge);
                        bHit = true;
                    }
                }
                if (!bHit)
                {
                    throw new InvalidOperationException("AlignData row not found for die " + dieKey + ". Do not append a new align row.");
                }
                table.Save(csvPath);
            }
        }

        public static void WriteWaferResult(string csvPath, string judge)
        {
            if (csvPath == null || csvPath == "")
            {
                throw new ArgumentException("csvPath");
            }
            string strJudge = NormalizeJudge(judge);
            if (strJudge != Good && strJudge != Ng)
            {
                throw new ArgumentException("judge must be GOOD or NG");
            }

            lock (objLock)
            {
                CsvTable table = CsvTable.Load(csvPath);
                table.EnsureVoidColumn();
                int nVoid = table.VoidColumnIndex();
                int i;
                for (i = 0; i < table.Rows.Length; i++)
                {
                    table.SetCell(i, nVoid, strJudge);
                }
                table.Save(csvPath);
            }
        }

        sealed class CsvTable
        {
            public string[] Header;
            public string[][] Rows;
            public bool HasHeader;

            public static CsvTable Load(string path)
            {
                if (!File.Exists(path))
                {
                    throw new FileNotFoundException("AlignData.csv not found. Write void result only after Align has created the file.", path);
                }

                string strText = ReadAllShare(path);
                string[] arrLine = SplitLines(strText);
                CsvTable table = new CsvTable();
                table.Header = new string[0];
                table.Rows = new string[0][];
                table.HasHeader = false;
                if (arrLine.Length == 0)
                {
                    throw new InvalidOperationException("AlignData.csv is empty. Do not FileMode.Create.");
                }

                string[] arrFirst = SplitCsv(arrLine[0]);
                table.HasHeader = LooksLikeHeader(arrFirst);
                int nStart = 0;
                if (table.HasHeader)
                {
                    table.Header = arrFirst;
                    nStart = 1;
                }

                int nRow = arrLine.Length - nStart;
                table.Rows = new string[nRow][];
                int i;
                for (i = 0; i < nRow; i++)
                {
                    table.Rows[i] = SplitCsv(arrLine[nStart + i]);
                }
                return table;
            }

            public void Save(string path)
            {
                StringBuilder sb = new StringBuilder();
                if (HasHeader)
                {
                    sb.AppendLine(JoinCsv(Header));
                }
                int i;
                for (i = 0; i < Rows.Length; i++)
                {
                    sb.AppendLine(JoinCsv(Rows[i]));
                }

                string strDir = Path.GetDirectoryName(path);
                if (strDir != null && strDir != "")
                {
                    Directory.CreateDirectory(strDir);
                }

                // Rewrite via temp so a failed Create does not leave AlignData.csv empty.
                string strTmp = path + ".voidtmp";
                WriteAllFlush(strTmp, sb.ToString());
                int nRetry = 0;
                while (nRetry < 8)
                {
                    try
                    {
                        File.Copy(strTmp, path, true);
                        File.Delete(strTmp);
                        return;
                    }
                    catch (IOException)
                    {
                        nRetry = nRetry + 1;
                        Thread.Sleep(20 * nRetry);
                    }
                }
                throw new IOException("AlignData.csv write failed: " + path);
            }

            static void WriteAllFlush(string path, string text)
            {
                FileStream fs = null;
                StreamWriter sw = null;
                try
                {
                    fs = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.ReadWrite);
                    sw = new StreamWriter(fs, Encoding.Default);
                    sw.NewLine = "\r\n";
                    sw.Write(text);
                    sw.Flush();
                    fs.Flush(true);
                }
                finally
                {
                    if (sw != null)
                    {
                        sw.Close();
                    }
                    if (fs != null)
                    {
                        fs.Close();
                    }
                }
            }

            public void EnsureVoidColumn()
            {
                if (HasHeader)
                {
                    int n = IndexOfHeader(VoidColumn);
                    if (n < 0)
                    {
                        Header = AppendCell(Header, VoidColumn);
                    }
                }
                int nNeed = ColumnCount();
                int i;
                for (i = 0; i < Rows.Length; i++)
                {
                    while (Rows[i].Length < nNeed)
                    {
                        Rows[i] = AppendCell(Rows[i], "");
                    }
                }
            }

            public int VoidColumnIndex()
            {
                if (HasHeader)
                {
                    int n = IndexOfHeader(VoidColumn);
                    if (n >= 0)
                    {
                        return n;
                    }
                }
                return ColumnCount() - 1;
            }

            public int FindKeyColumn(int fallbackIndex)
            {
                if (HasHeader)
                {
                    string[] arrName = new string[] { "No", "Die", "Index", "DieNo", "Site", "ID" };
                    int i;
                    for (i = 0; i < arrName.Length; i++)
                    {
                        int n = IndexOfHeader(arrName[i]);
                        if (n >= 0)
                        {
                            return n;
                        }
                    }
                }
                if (fallbackIndex < 0)
                {
                    return 0;
                }
                return fallbackIndex;
            }

            public void SetCell(int row, int col, string value)
            {
                while (Rows[row].Length <= col)
                {
                    Rows[row] = AppendCell(Rows[row], "");
                }
                Rows[row][col] = value;
            }

            int ColumnCount()
            {
                int n = HasHeader ? Header.Length : 0;
                int i;
                for (i = 0; i < Rows.Length; i++)
                {
                    if (Rows[i].Length > n)
                    {
                        n = Rows[i].Length;
                    }
                }
                if (n < 1)
                {
                    n = 1;
                }
                return n;
            }

            int IndexOfHeader(string name)
            {
                int i;
                for (i = 0; i < Header.Length; i++)
                {
                    if (string.Compare(Header[i].Trim(), name, true) == 0)
                    {
                        return i;
                    }
                }
                return -1;
            }

            static bool LooksLikeHeader(string[] arr)
            {
                if (arr.Length == 0)
                {
                    return false;
                }
                int i;
                for (i = 0; i < arr.Length; i++)
                {
                    string str = arr[i].Trim();
                    if (str.Length == 0)
                    {
                        continue;
                    }
                    double d;
                    if (double.TryParse(str, out d))
                    {
                        return false;
                    }
                }
                string str0 = arr[0].Trim();
                if (string.Compare(str0, "No", true) == 0)
                {
                    return true;
                }
                if (string.Compare(str0, "Die", true) == 0)
                {
                    return true;
                }
                if (str0.IndexOf("Offset", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    return true;
                }
                if (str0.IndexOf("Pos", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    return true;
                }
                return arr.Length >= 2;
            }

            static string[] AppendCell(string[] arr, string value)
            {
                string[] arrNew = new string[arr.Length + 1];
                int i;
                for (i = 0; i < arr.Length; i++)
                {
                    arrNew[i] = arr[i];
                }
                arrNew[arr.Length] = value;
                return arrNew;
            }

            static string[] SplitLines(string text)
            {
                string str = text.Replace("\r\n", "\n").Replace('\r', '\n');
                string[] arr = str.Split('\n');
                int n = arr.Length;
                while (n > 0 && arr[n - 1].Trim() == "")
                {
                    n = n - 1;
                }
                if (n == arr.Length)
                {
                    return arr;
                }
                string[] arrNew = new string[n];
                int i;
                for (i = 0; i < n; i++)
                {
                    arrNew[i] = arr[i];
                }
                return arrNew;
            }

            static string[] SplitCsv(string line)
            {
                return line.Split(',');
            }

            static string JoinCsv(string[] arr)
            {
                return string.Join(",", arr);
            }

            static string ReadAllShare(string path)
            {
                FileStream fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
                StreamReader sr = new StreamReader(fs, Encoding.Default);
                try
                {
                    return sr.ReadToEnd();
                }
                finally
                {
                    sr.Close();
                    fs.Close();
                }
            }
        }
    }
}
