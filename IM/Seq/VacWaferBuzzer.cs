using System;

namespace WISVision
{
    /// <summary>
    /// 0910 load/unload vacuum delay wafer check vs buzzer3.
    ///
    /// 이 파일은 현장 IM 원본이 아니다.
    /// GitHub 에 0910 소스가 없어서 증상으로 재구성했다.
    ///
    /// 증상
    ///   setBuzzer 가 true 가 되는 load / unload seq
    ///   설비 중 한 호기, 간헐
    ///   load 시 buzzer3 켜짐
    ///   unload 시 buzzer3 꺼짐
    ///
    /// 의심 식 (현장 VS 에서 이 모양을 찾아라)
    ///   SetVacuum(bLoad);
    ///   Thread.Sleep(nVacDelay);
    ///   setBuzzer = !CheckWafer();
    ///   SetBuzzer(3, setBuzzer);
    ///
    /// 고치는 쪽
    ///   1) 고정 Sleep 후 1회 체크 금지. 센서가 기대값될 때까지 Wait.
    ///   2) 작업자 알림 부저와 웨이퍼 미싱 알람을 같은 비트로 묶지 말 것.
    ///
    ///   bool bOk = VacWaferBuzzer.WaitWafer(CheckWafer, bLoad, nVacTimeout, 20);
    ///   VacWaferBuzzer.PulseBuzzer3(SetBuzzer3, bNotify, nBuzzerMs);
    /// </summary>
    public static class VacWaferBuzzer
    {
        public const int BuzzerNo = 3;
        public const int DefaultPollMs = 20;

        /// <summary>
        /// 0910 의심 식. 웨이퍼가 없으면 setBuzzer true.
        /// </summary>
        public static bool SetBuzzerFromWaferMissing(bool bWaferPresent)
        {
            return !bWaferPresent;
        }

        public static bool WaitWafer(Func<bool> fnCheckWafer, bool bExpectPresent, int nTimeoutMs)
        {
            return WaitWafer(fnCheckWafer, bExpectPresent, nTimeoutMs, DefaultPollMs, SleepMs);
        }

        public static bool WaitWafer(Func<bool> fnCheckWafer, bool bExpectPresent, int nTimeoutMs, int nPollMs)
        {
            return WaitWafer(fnCheckWafer, bExpectPresent, nTimeoutMs, nPollMs, SleepMs);
        }

        public static bool WaitWafer(Func<bool> fnCheckWafer, bool bExpectPresent, int nTimeoutMs, int nPollMs, Action<int> fnSleep)
        {
            if (fnCheckWafer == null)
            {
                return false;
            }
            if (fnSleep == null)
            {
                fnSleep = SleepMs;
            }
            if (nPollMs < 1)
            {
                nPollMs = DefaultPollMs;
            }

            int nElapsed = 0;
            while (nElapsed <= nTimeoutMs)
            {
                if (fnCheckWafer() == bExpectPresent)
                {
                    return true;
                }
                fnSleep(nPollMs);
                nElapsed = nElapsed + nPollMs;
            }
            return fnCheckWafer() == bExpectPresent;
        }

        /// <summary>
        /// 작업자 알림 펄스. CheckWafer 결과와 분리한다.
        /// bSetBuzzer 가 false 면 아무 것도 안 한다.
        /// </summary>
        public static void PulseBuzzer3(Action<bool> fnSetBuzzer3, bool bSetBuzzer, int nOnMs)
        {
            PulseBuzzer3(fnSetBuzzer3, bSetBuzzer, nOnMs, SleepMs);
        }

        public static void PulseBuzzer3(Action<bool> fnSetBuzzer3, bool bSetBuzzer, int nOnMs, Action<int> fnSleep)
        {
            if (!bSetBuzzer)
            {
                return;
            }
            if (fnSetBuzzer3 == null)
            {
                return;
            }
            if (fnSleep == null)
            {
                fnSleep = SleepMs;
            }
            fnSetBuzzer3(true);
            if (nOnMs > 0)
            {
                fnSleep(nOnMs);
            }
            fnSetBuzzer3(false);
        }

        /// <summary>
        /// 진공 지령 후 센서 대기. load 는 present=true, unload 는 present=false.
        /// </summary>
        public static bool RunVacThenCheck(Action<bool> fnSetVacuum, Func<bool> fnCheckWafer, bool bVacuumOn, int nTimeoutMs, int nPollMs)
        {
            return RunVacThenCheck(fnSetVacuum, fnCheckWafer, bVacuumOn, nTimeoutMs, nPollMs, SleepMs);
        }

        public static bool RunVacThenCheck(Action<bool> fnSetVacuum, Func<bool> fnCheckWafer, bool bVacuumOn, int nTimeoutMs, int nPollMs, Action<int> fnSleep)
        {
            if (fnSetVacuum == null)
            {
                return false;
            }
            fnSetVacuum(bVacuumOn);
            return WaitWafer(fnCheckWafer, bVacuumOn, nTimeoutMs, nPollMs, fnSleep);
        }

        static void SleepMs(int nMs)
        {
            if (nMs > 0)
            {
                System.Threading.Thread.Sleep(nMs);
            }
        }
    }
}
