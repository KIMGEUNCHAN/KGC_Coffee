using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;

namespace WISVision
{
    /// <summary>
    /// WISVision IM AOI 단축키.
    ///
    /// 설정
    ///   C:\WISVision\Config\AOIKeys.ini
    ///
    /// 로그 (clsLog 와 같은 자리)
    ///   C:\WISVision\Log\AOIKeys_LAST.txt
    ///   C:\WISVision\Log\{날짜}\AOIKeys_{날짜}.txt
    ///
    /// 호출
    ///   clsAOIKeys.Load();
    ///   string strAction = clsAOIKeys.ProcessKey((int)e.KeyData);
    ///   int nClass = clsAOIKeys.ClassNoFromAction(strAction);
    ///
    /// Form.KeyPreview = true 로 두고 KeyDown 에서 KeyData 를 넘긴다.
    /// KeyCode 만 넘기면 Ctrl/Alt/Shift 조합이 빠진다.
    /// </summary>
    public class clsAOIKeys
    {
        public const string ModuleName = "AOIKeys";
        public static string strConfigPath = @"C:\WISVision\Config\AOIKeys.ini";
        public static string strLogPath = @"C:\WISVision\Log";

        public const int MOD_SHIFT = 0x00010000;
        public const int MOD_CONTROL = 0x00020000;
        public const int MOD_ALT = 0x00040000;
        public const int KEY_CODE_MASK = 0x0000FFFF;
        public const int MOD_MASK = MOD_SHIFT | MOD_CONTROL | MOD_ALT;

        static readonly object objLock = new object();
        static readonly string[] arrDateFmt = new string[] { "yyyyMMdd", "yyyy-MM-dd", "yyyy_MM_dd" };
        static readonly Dictionary<string, int> mapKeyCodes = BuildKeyCodes();
        static readonly Dictionary<int, string> mapKeyNames = BuildKeyNames();

        static Dictionary<int, string> mapKeyToAction = new Dictionary<int, string>();
        static Dictionary<string, List<int>> mapActionToKeys = new Dictionary<string, List<int>>();
        static bool bLoaded = false;

        public static readonly string[] AOI_ACTIONS = new string[]
        {
            "Start", "Stop", "Pause", "Auto", "Manual",
            "Grab", "Live", "Align",
            "OK", "NG", "Retry", "Skip",
            "Next", "Prev", "NextRow", "PrevRow", "Home",
            "Save", "Recipe",
            "Class1", "Class2", "Class3", "Class4", "Class5",
            "Class6", "Class7", "Class8", "Class9"
        };

        static clsAOIKeys()
        {
            ApplyDefaults();
            bLoaded = true;
        }

        public static void Load()
        {
            Load(strConfigPath);
        }

        public static void Load(string strPath)
        {
            Dictionary<string, string> mapBind = DefaultBindings();
            if (strPath != null && strPath != "" && File.Exists(strPath))
            {
                Dictionary<string, string> mapFile = ReadIni(strPath);
                foreach (KeyValuePair<string, string> kv in mapFile)
                {
                    mapBind[kv.Key] = kv.Value;
                }
            }

            lock (objLock)
            {
                mapKeyToAction.Clear();
                mapActionToKeys.Clear();
                foreach (KeyValuePair<string, string> kv in mapBind)
                {
                    try
                    {
                        BindAction(kv.Key, ParseKeyList(kv.Value));
                    }
                    catch (Exception)
                    {
                    }
                }
                bLoaded = true;
            }
        }

        public static void SaveDefault()
        {
            SaveDefault(strConfigPath);
        }

        public static void SaveDefault(string strPath)
        {
            string strDir = Path.GetDirectoryName(strPath);
            if (strDir != null && strDir != "")
            {
                Directory.CreateDirectory(strDir);
            }
            File.WriteAllText(strPath, DefaultIniText(), Encoding.Default);
            Load(strPath);
        }

        public static void Bind(string strAction, string strKeys)
        {
            if (strAction == null || strAction.Trim() == "")
            {
                return;
            }
            lock (objLock)
            {
                BindAction(strAction.Trim(), ParseKeyList(strKeys));
            }
        }

        public static void BindClass(int nClass, string strKeys)
        {
            if (nClass < 1 || nClass > 9)
            {
                return;
            }
            Bind("Class" + nClass.ToString(), strKeys);
        }

        public static int ParseKey(string strKey)
        {
            return ParseKeyValue(strKey);
        }

        public static string KeyName(int nKeyData)
        {
            return KeyNameFromCode(nKeyData);
        }

        public static string TryGetAction(int nKeyData)
        {
            EnsureLoaded();
            int nCode = Normalize(nKeyData);
            if (nCode == 0)
            {
                return "";
            }
            lock (objLock)
            {
                if (mapKeyToAction.ContainsKey(nCode))
                {
                    return mapKeyToAction[nCode];
                }
            }
            return "";
        }

        public static string TryGetAction(string strKey)
        {
            int nCode;
            try
            {
                nCode = ParseKeyValue(strKey);
            }
            catch (Exception)
            {
                return "";
            }
            return TryGetAction(nCode);
        }

        public static string ProcessKey(int nKeyData)
        {
            string strAction = TryGetAction(nKeyData);
            if (strAction != "")
            {
                WriteKeyLog(strAction, KeyNameFromCode(nKeyData));
            }
            return strAction;
        }

        public static string ProcessKey(string strKey)
        {
            string strAction = TryGetAction(strKey);
            if (strAction != "")
            {
                WriteKeyLog(strAction, strKey);
            }
            return strAction;
        }

        public static int ClassNoFromAction(string strAction)
        {
            if (strAction == null)
            {
                return 0;
            }
            string strText = strAction.Trim();
            if (strText.Length < 6)
            {
                return 0;
            }
            if (string.Compare(strText, 0, "Class", 0, 5, true) != 0)
            {
                return 0;
            }
            string strNo = strText.Substring(5);
            int nClass;
            if (!int.TryParse(strNo, out nClass))
            {
                return 0;
            }
            if (nClass < 1 || nClass > 9)
            {
                return 0;
            }
            return nClass;
        }

        public static void WriteKeyLog(string strAction, string strKey)
        {
            WriteKeyLog(strAction, strKey, false);
        }

        public static void WriteKeyLog(string strAction, string strKey, bool bNewLast)
        {
            string strMsg = strAction == null ? "" : strAction.Trim();
            string strKeyText = strKey == null ? "" : strKey.Trim();
            if (strKeyText != "")
            {
                if (strMsg != "")
                {
                    strMsg = "Action=" + strMsg + " Key=" + strKeyText;
                }
                else
                {
                    strMsg = "Key=" + strKeyText;
                }
            }
            else if (strMsg != "")
            {
                strMsg = "Action=" + strMsg;
            }

            lock (objLock)
            {
                DateTime dtNow = DateTime.Now;
                string strDate = GetDateStamp(dtNow);
                string strDir = Path.Combine(strLogPath, strDate);
                string strDaily = Path.Combine(strDir, ModuleName + "_" + strDate + ".txt");
                string strLast = Path.Combine(strLogPath, ModuleName + "_LAST.txt");
                string strLine = dtNow.ToString("yyyy-MM-dd HH:mm:ss.fff") + " : " + strMsg;

                Directory.CreateDirectory(strLogPath);
                Directory.CreateDirectory(strDir);

                WriteLineFlush(strLast, strLine, bNewLast);
                WriteLineFlush(strDaily, strLine, false);
            }
        }

        static void EnsureLoaded()
        {
            if (!bLoaded)
            {
                Load();
            }
        }

        static void ApplyDefaults()
        {
            mapKeyToAction.Clear();
            mapActionToKeys.Clear();
            Dictionary<string, string> mapBind = DefaultBindings();
            foreach (KeyValuePair<string, string> kv in mapBind)
            {
                BindAction(kv.Key, ParseKeyList(kv.Value));
            }
        }

        static void BindAction(string strAction, List<int> listCode)
        {
            if (mapActionToKeys.ContainsKey(strAction))
            {
                List<int> listOld = mapActionToKeys[strAction];
                int i;
                for (i = 0; i < listOld.Count; i++)
                {
                    if (mapKeyToAction.ContainsKey(listOld[i]) && mapKeyToAction[listOld[i]] == strAction)
                    {
                        mapKeyToAction.Remove(listOld[i]);
                    }
                }
            }

            List<int> listNew = new List<int>();
            int k;
            for (k = 0; k < listCode.Count; k++)
            {
                int nCode = listCode[k];
                if (nCode == 0)
                {
                    continue;
                }
                mapKeyToAction[nCode] = strAction;
                if (!listNew.Contains(nCode))
                {
                    listNew.Add(nCode);
                }
            }
            if (listNew.Count > 0)
            {
                mapActionToKeys[strAction] = listNew;
            }
            else
            {
                mapActionToKeys.Remove(strAction);
            }
        }

        static List<int> ParseKeyList(string strKeys)
        {
            List<int> list = new List<int>();
            if (strKeys == null || strKeys.Trim() == "")
            {
                return list;
            }
            string[] arr = strKeys.Split(',');
            int i;
            for (i = 0; i < arr.Length; i++)
            {
                string strPart = arr[i].Trim();
                if (strPart == "")
                {
                    continue;
                }
                try
                {
                    int nCode = ParseKeyValue(strPart);
                    if (nCode != 0)
                    {
                        list.Add(nCode);
                    }
                }
                catch (Exception)
                {
                }
            }
            return list;
        }

        static int ParseKeyValue(string strKey)
        {
            if (strKey == null)
            {
                return 0;
            }
            string strRaw = strKey.Trim();
            if (strRaw == "")
            {
                return 0;
            }

            int nAllDigit;
            if (strRaw.Length > 2 && int.TryParse(strRaw, out nAllDigit))
            {
                return Normalize(nAllDigit);
            }

            strRaw = strRaw.Replace('-', '+');
            string[] arr = strRaw.Split('+');
            if (arr.Length == 0)
            {
                return 0;
            }

            int nMods = 0;
            int i;
            for (i = 0; i < arr.Length - 1; i++)
            {
                string strMod = arr[i].Trim().ToUpper();
                strMod = strMod.Replace(" ", "");
                if (strMod == "CTRL" || strMod == "CONTROL")
                {
                    nMods = nMods | MOD_CONTROL;
                }
                else if (strMod == "ALT" || strMod == "MENU")
                {
                    nMods = nMods | MOD_ALT;
                }
                else if (strMod == "SHIFT")
                {
                    nMods = nMods | MOD_SHIFT;
                }
                else
                {
                    throw new ArgumentException("unknown modifier: " + arr[i]);
                }
            }

            int nKey = LookupKeyToken(arr[arr.Length - 1]);
            if (nKey == 0)
            {
                throw new ArgumentException("unknown key: " + arr[arr.Length - 1]);
            }
            return Normalize(nMods | nKey);
        }

        static int LookupKeyToken(string strToken)
        {
            if (strToken == null)
            {
                return 0;
            }
            string strName = strToken.Trim().ToUpper().Replace(" ", "");
            if (strName.StartsWith("VK_"))
            {
                strName = strName.Substring(3);
            }
            if (strName.StartsWith("KEYS."))
            {
                strName = strName.Substring(5);
            }
            if (mapKeyCodes.ContainsKey(strName))
            {
                return mapKeyCodes[strName];
            }
            return 0;
        }

        static string KeyNameFromCode(int nKeyData)
        {
            int nCode = Normalize(nKeyData);
            if (nCode == 0)
            {
                return "";
            }
            string strName = "";
            if ((nCode & MOD_CONTROL) != 0)
            {
                strName = strName + "Ctrl+";
            }
            if ((nCode & MOD_ALT) != 0)
            {
                strName = strName + "Alt+";
            }
            if ((nCode & MOD_SHIFT) != 0)
            {
                strName = strName + "Shift+";
            }
            int nBase = nCode & KEY_CODE_MASK;
            if (mapKeyNames.ContainsKey(nBase))
            {
                strName = strName + mapKeyNames[nBase];
            }
            else
            {
                strName = strName + "0x" + nBase.ToString("X2");
            }
            return strName;
        }

        static int Normalize(int nCode)
        {
            return (nCode & KEY_CODE_MASK) | (nCode & MOD_MASK);
        }

        static Dictionary<string, string> DefaultBindings()
        {
            Dictionary<string, string> map = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            map["Start"] = "F5";
            map["Stop"] = "Escape";
            map["Pause"] = "F6";
            map["Auto"] = "F4";
            map["Manual"] = "F3";
            map["Grab"] = "F2";
            map["Live"] = "F1";
            map["Align"] = "A";
            map["OK"] = "Enter";
            map["NG"] = "Space";
            map["Retry"] = "R";
            map["Skip"] = "S";
            map["Next"] = "Right";
            map["Prev"] = "Left";
            map["NextRow"] = "Down";
            map["PrevRow"] = "Up";
            map["Home"] = "Home";
            map["Save"] = "F9";
            map["Recipe"] = "F10";
            map["Class1"] = "D1,NumPad1";
            map["Class2"] = "D2,NumPad2";
            map["Class3"] = "D3,NumPad3";
            map["Class4"] = "D4,NumPad4";
            map["Class5"] = "D5,NumPad5";
            map["Class6"] = "D6,NumPad6";
            map["Class7"] = "D7,NumPad7";
            map["Class8"] = "D8,NumPad8";
            map["Class9"] = "D9,NumPad9";
            return map;
        }

        static Dictionary<string, string> ReadIni(string strPath)
        {
            Dictionary<string, string> map = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            string strText = ReadText(strPath);
            string[] arrLine = strText.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
            bool bSection = true;
            int i;
            for (i = 0; i < arrLine.Length; i++)
            {
                string strLine = arrLine[i].Trim();
                if (strLine == "" || strLine.StartsWith(";") || strLine.StartsWith("#"))
                {
                    continue;
                }
                if (strLine.StartsWith("[") && strLine.EndsWith("]"))
                {
                    string strSec = strLine.Substring(1, strLine.Length - 2).Trim();
                    string strLow = strSec.ToLower();
                    bSection = (strLow == "" || strLow == "aoikeys" || strLow == "keys");
                    continue;
                }
                if (!bSection)
                {
                    continue;
                }
                int nEq = strLine.IndexOf('=');
                if (nEq <= 0)
                {
                    continue;
                }
                string strAction = strLine.Substring(0, nEq).Trim();
                string strValue = strLine.Substring(nEq + 1).Trim();
                if (strAction != "")
                {
                    map[strAction] = strValue;
                }
            }
            return map;
        }

        static string ReadText(string strPath)
        {
            byte[] arr = File.ReadAllBytes(strPath);
            if (arr.Length >= 3 && arr[0] == 0xEF && arr[1] == 0xBB && arr[2] == 0xBF)
            {
                return Encoding.UTF8.GetString(arr, 3, arr.Length - 3);
            }
            try
            {
                return Encoding.UTF8.GetString(arr);
            }
            catch (Exception)
            {
                return Encoding.Default.GetString(arr);
            }
        }

        static string DefaultIniText()
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("; WISVision IM AOI Keys");
            sb.AppendLine("; 경로: C:\\WISVision\\Config\\AOIKeys.ini");
            sb.AppendLine("; 한 줄: 동작=키   (여러 키는 콤마)");
            sb.AppendLine("; 주석: ; 또는 #");
            sb.AppendLine("; 키 예: F5, Enter, Escape, Space, Left, D1, NumPad1, Ctrl+F5");
            sb.AppendLine("");
            sb.AppendLine("[AOIKeys]");
            sb.AppendLine("; 운전");
            sb.AppendLine("Start=F5");
            sb.AppendLine("Stop=Escape");
            sb.AppendLine("Pause=F6");
            sb.AppendLine("Auto=F4");
            sb.AppendLine("Manual=F3");
            sb.AppendLine("");
            sb.AppendLine("; 촬상 / 정렬");
            sb.AppendLine("Grab=F2");
            sb.AppendLine("Live=F1");
            sb.AppendLine("Align=A");
            sb.AppendLine("");
            sb.AppendLine("; 판정");
            sb.AppendLine("OK=Enter");
            sb.AppendLine("NG=Space");
            sb.AppendLine("Retry=R");
            sb.AppendLine("Skip=S");
            sb.AppendLine("");
            sb.AppendLine("; 맵 이동");
            sb.AppendLine("Next=Right");
            sb.AppendLine("Prev=Left");
            sb.AppendLine("NextRow=Down");
            sb.AppendLine("PrevRow=Up");
            sb.AppendLine("Home=Home");
            sb.AppendLine("");
            sb.AppendLine("; 저장 / 레시피");
            sb.AppendLine("Save=F9");
            sb.AppendLine("Recipe=F10");
            sb.AppendLine("");
            sb.AppendLine("; 불량 코드 1~9 (숫자키 + 키패드)");
            sb.AppendLine("Class1=D1,NumPad1");
            sb.AppendLine("Class2=D2,NumPad2");
            sb.AppendLine("Class3=D3,NumPad3");
            sb.AppendLine("Class4=D4,NumPad4");
            sb.AppendLine("Class5=D5,NumPad5");
            sb.AppendLine("Class6=D6,NumPad6");
            sb.AppendLine("Class7=D7,NumPad7");
            sb.AppendLine("Class8=D8,NumPad8");
            sb.AppendLine("Class9=D9,NumPad9");
            return sb.ToString();
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

        static Dictionary<string, int> BuildKeyCodes()
        {
            Dictionary<string, int> map = new Dictionary<string, int>();
            map["BACK"] = 8;
            map["BACKSPACE"] = 8;
            map["TAB"] = 9;
            map["ENTER"] = 13;
            map["RETURN"] = 13;
            map["ESCAPE"] = 27;
            map["ESC"] = 27;
            map["SPACE"] = 32;
            map["SPACEBAR"] = 32;
            map["PAGEUP"] = 33;
            map["PRIOR"] = 33;
            map["PAGEDOWN"] = 34;
            map["PAGEDN"] = 34;
            map["END"] = 35;
            map["HOME"] = 36;
            map["LEFT"] = 37;
            map["UP"] = 38;
            map["RIGHT"] = 39;
            map["DOWN"] = 40;
            map["INSERT"] = 45;
            map["INS"] = 45;
            map["DELETE"] = 46;
            map["DEL"] = 46;
            int i;
            for (i = 0; i <= 9; i++)
            {
                map["D" + i.ToString()] = 48 + i;
                map[i.ToString()] = 48 + i;
                map["NUMPAD" + i.ToString()] = 96 + i;
            }
            string strAlpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
            for (i = 0; i < strAlpha.Length; i++)
            {
                map[strAlpha.Substring(i, 1)] = 65 + i;
            }
            for (i = 1; i <= 24; i++)
            {
                map["F" + i.ToString()] = 111 + i;
            }
            return map;
        }

        static Dictionary<int, string> BuildKeyNames()
        {
            Dictionary<int, string> map = new Dictionary<int, string>();
            map[8] = "Backspace";
            map[9] = "Tab";
            map[13] = "Enter";
            map[27] = "Escape";
            map[32] = "Space";
            map[33] = "PageUp";
            map[34] = "PageDown";
            map[35] = "End";
            map[36] = "Home";
            map[37] = "Left";
            map[38] = "Up";
            map[39] = "Right";
            map[40] = "Down";
            map[45] = "Insert";
            map[46] = "Delete";
            int i;
            for (i = 0; i <= 9; i++)
            {
                map[48 + i] = "D" + i.ToString();
                map[96 + i] = "NumPad" + i.ToString();
            }
            string strAlpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
            for (i = 0; i < strAlpha.Length; i++)
            {
                map[65 + i] = strAlpha.Substring(i, 1);
            }
            for (i = 1; i <= 24; i++)
            {
                map[111 + i] = "F" + i.ToString();
            }
            return map;
        }
    }
}
