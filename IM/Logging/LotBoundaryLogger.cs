using System;
using WISVision;

namespace IM.Logging
{
    /// <summary>
    /// LotBoundary 전용 래퍼. 실제 기록은 기존 WISVision clsLog.WriteLog 와 같다.
    ///
    ///   clsLog.WriteLog("LotBoundary", "FindEdge OK");
    ///   LotBoundaryLogger.Write("FindEdge OK");   // 동일
    /// </summary>
    public static class LotBoundaryLogger
    {
        public const string ModuleName = "LotBoundary";

        public static string LogRoot
        {
            get { return clsLog.strLogPath; }
            set { clsLog.strLogPath = value; }
        }

        public static void BeginLot(string lotId)
        {
            clsLog.WriteLog(ModuleName, "Lot Start : " + NullToEmpty(lotId), true);
        }

        public static void EndLot(string lotId, string result)
        {
            clsLog.WriteLog(ModuleName, "Lot End : " + NullToEmpty(lotId) + " Result=" + NullToEmpty(result));
        }

        public static void Write(string message)
        {
            clsLog.WriteLog(ModuleName, message);
        }

        static string NullToEmpty(string value)
        {
            return value == null ? string.Empty : value;
        }
    }
}
