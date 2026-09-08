using System;
using System.IO;
using System.Text;
using System.Threading;

namespace WISVision
{
    /// <summary>
    /// WISVision 기존 로그 방식.
    ///
    ///   clsLog.WriteLog("Inspect", "Align OK");
    ///   clsLog.WriteLog("LotBoundary", "FindEdge OK");
    ///
    /// 파일
    ///   C:\WISVision\Log\{Name}_LAST.txt
    ///   C:\WISVision\Log\{날짜}\{Name}_{날짜}.txt
    ///
    /// 날짜 폴더는 기존 WISVision 폴더를 그대로 쓴다.
    /// 한 줄 형식: yyyy-MM-dd HH:mm:ss.fff : 메시지
    /// 매번 StreamWriter 닫고 FileStream.Flush(true) 해서 즉시 디스크에 남긴다.
    /// </summary>
    public class clsLog
    {
        public static string strLogPath = @"C:\WISVision\Log";

        static readonly object objLock = new object();
        static readonly string[] arrDateFmt = new string[] { "yyyyMMdd", "yyyy-MM-dd", "yyyy_MM_dd" };

        public static void WriteLog(string strLog)
        {
            WriteLog("System", strLog, false);
        }

        public static void WriteLog(string strName, string strLog)
        {
            WriteLog(strName, strLog, false);
        }

        /// <param name="bNewLast">true 이면 LAST 파일을 비우고 새로 쓴다 (Lot 시작).</param>
        public static void WriteLog(string strName, string strLog, bool bNewLast)
        {
            if (strName == null || strName == "")
            {
                strName = "System";
            }
            if (strLog == null)
            {
                strLog = "";
            }

            lock (objLock)
            {
                DateTime dtNow = DateTime.Now;
                string strDate = GetDateStamp(dtNow);
                string strDir = Path.Combine(strLogPath, strDate);
                string strDaily = Path.Combine(strDir, strName + "_" + strDate + ".txt");
                string strLast = Path.Combine(strLogPath, strName + "_LAST.txt");
                string strLine = dtNow.ToString("yyyy-MM-dd HH:mm:ss.fff") + " : " + strLog;

                Directory.CreateDirectory(strLogPath);
                Directory.CreateDirectory(strDir);

                WriteLineFlush(strLast, strLine, bNewLast);
                WriteLineFlush(strDaily, strLine, false);
            }
        }

        static string GetDateStamp(DateTime dtNow)
        {
            int i;
            for (i = 0; i < arrDateFmt.Length; i++)
            {
                string strStamp = dtNow.ToString(arrDateFmt[i]);
                if (Directory.Exists(Path.Combine(strLogPath, strStamp)))
                {
                    return strStamp;
                }
            }
            return dtNow.ToString("yyyyMMdd");
        }

        static void WriteLineFlush(string strFile, string strLine, bool bNewFile)
        {
            FileMode eMode = FileMode.Append;
            if (bNewFile || !File.Exists(strFile))
            {
                eMode = FileMode.Create;
            }

            FileStream fs = null;
            StreamWriter sw = null;
            int nRetry = 0;
            while (nRetry < 8)
            {
                try
                {
                    fs = new FileStream(strFile, eMode, FileAccess.Write, FileShare.ReadWrite);
                    sw = new StreamWriter(fs, Encoding.Default);
                    sw.AutoFlush = true;
                    sw.WriteLine(strLine);
                    sw.Flush();
                    fs.Flush(true);
                    return;
                }
                catch (IOException)
                {
                    nRetry = nRetry + 1;
                    Thread.Sleep(20 * nRetry);
                }
                finally
                {
                    if (sw != null)
                    {
                        sw.Close();
                        sw = null;
                    }
                    if (fs != null)
                    {
                        fs.Close();
                        fs = null;
                    }
                }
            }
        }
    }
}
