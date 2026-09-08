using System;
using WISVision;

namespace IM.Logging
{
    /// <summary>
    /// Edge Profiling NG 복구 팝업 3버튼 로그 맵.
    ///
    /// 이 파일은 현장 IM 원본이 아니다.
    /// 현장 소스의 Unload / Manual Remove / Retry 분기에
    /// 아래 WriteLog 가 들어있는지 대조하거나, 없으면 이 호출을 넣는다.
    ///
    /// 실제 팝업 ShowDialog 는 현장 폼에 있다.
    /// 키보드 AOIKeys Manual=F3 / Retry=R 과 다른 경로다.
    ///
    ///   EdgeProfilingNgRecovery.OnEdgeProfilingNg("offset over");
    ///   EdgeProfilingNgRecovery.OnUnload();
    ///   EdgeProfilingNgRecovery.OnManualRemove();
    ///   EdgeProfilingNgRecovery.OnRetry(2);
    /// </summary>
    public static class EdgeProfilingNgRecovery
    {
        public const string InspectModule = "Inspect";
        public const string AlarmModule = "Alarm";
        public const string ParentAlarm = "IM Inspection Error";

        public enum OperatorChoice
        {
            Unload = 0,
            ManualRemove = 1,
            Retry = 2
        }

        public static void OnEdgeProfilingNg()
        {
            OnEdgeProfilingNg("");
        }

        public static void OnEdgeProfilingNg(string reason)
        {
            string strMsg = "EdgeProfiling NG";
            if (reason != null && reason != "")
            {
                strMsg = strMsg + " " + reason;
            }
            clsLog.WriteLog(InspectModule, strMsg);
            clsLog.WriteLog(AlarmModule, "EdgeProfiling NG popup Unload/ManualRemove/Retry");
        }

        public static void OnOperatorChoice(OperatorChoice choice)
        {
            OnOperatorChoice(choice, 0);
        }

        public static void OnOperatorChoice(OperatorChoice choice, int retryCount)
        {
            if (choice == OperatorChoice.Unload)
            {
                OnUnload();
            }
            else if (choice == OperatorChoice.ManualRemove)
            {
                OnManualRemove();
            }
            else if (choice == OperatorChoice.Retry)
            {
                OnRetry(retryCount);
            }
        }

        /// <summary>
        /// Unload: 로컬 로그 + 상위 IM Inspection Error + 로봇 언로드.
        /// </summary>
        public static void OnUnload()
        {
            clsLog.WriteLog(InspectModule, "EdgeProfiling NG Operator=Unload");
            clsLog.WriteLog(AlarmModule, ParentAlarm);
        }

        /// <summary>
        /// Manual Remove: 로컬 로그만. IM Inspection Error 를 올리지 않는다.
        /// 로봇 언로드 없이 작업자가 웨이퍼를 직접 제거한다.
        /// </summary>
        public static void OnManualRemove()
        {
            clsLog.WriteLog(InspectModule, "EdgeProfiling NG Operator=ManualRemove");
        }

        public static void OnManualRemoveConfirmed()
        {
            clsLog.WriteLog(InspectModule, "EdgeProfiling NG Operator=ManualRemove Confirmed");
        }

        /// <summary>
        /// Retry: 로컬 로그만. IM Inspection Error 없음.
        /// 같은 웨이퍼로 Edge Profiling 을 다시 탄다.
        /// </summary>
        public static void OnRetry(int retryCount)
        {
            clsLog.WriteLog(InspectModule, "EdgeProfiling NG Operator=Retry Count=" + retryCount.ToString());
        }
    }
}
