#include <iostream>
#include <string>
#include <unordered_map>
#include <climits>

using namespace std;

/**
 * LeetCode Problem 76: Minimum Window Substring
 * 
 * Problem Statement:
 * Given two strings s and t of lengths m and n respectively, return the minimum window 
 * substring of s such that every character in t (including duplicates) is included in the window.
 * If there is no such window in s that covers all characters in t, return the empty string "".
 * 
 * The testcases will be generated such that the answer is unique.
 * 
 * Example 1:
 * Input: s = "ADOBECODEBANC", t = "ABC"
 * Output: "ADOBEC"
 * 
 * Example 2:
 * Input: s = "a", t = "a"
 * Output: "a"
 * 
 * Example 3:
 * Input: s = "a", t = "aa"
 * Output: ""
 * 
 * Constraints:
 * - m == s.length
 * - n == t.length
 * - 1 <= m, n <= 10^5
 * - s and t consist of uppercase and lowercase English letters.
 * 
 * Time Complexity: O(m + n) where m is the length of s and n is the length of t
 * Space Complexity: O(1) since we store at most 52 characters (26 lowercase + 26 uppercase)
 */

class Solution {
public:
    string minWindow(string s, string t) {
        // Edge case: if t is longer than s, no valid window exists
        if (t.length() > s.length()) {
            return "";
        }
        
        // Create a frequency map for characters in t
        unordered_map<char, int> tCount;
        for (char c : t) {
            tCount[c]++;
        }
        
        // Create a frequency map for characters in the current window
        unordered_map<char, int> windowCount;
        
        // Number of unique characters in t that need to be present in the window
        int required = tCount.size();
        
        // Number of unique characters in the current window that have the desired frequency
        int formed = 0;
        
        // Left and right pointers for the sliding window
        int left = 0, right = 0;
        
        // Variables to store the result
        int minLen = INT_MAX;
        int minLeft = 0;
        
        // Expand the window by moving right pointer
        while (right < s.length()) {
            // Add character from the right to the window
            char c = s[right];
            windowCount[c]++;
            
            // If the frequency of the current character matches the desired frequency in t
            if (tCount.count(c) && windowCount[c] == tCount[c]) {
                formed++;
            }
            
            // Try to contract the window until it ceases to be 'desirable'
            while (left <= right && formed == required) {
                // Save the smallest window until now
                if (right - left + 1 < minLen) {
                    minLen = right - left + 1;
                    minLeft = left;
                }
                
                // Remove character from the left of the window
                char leftChar = s[left];
                windowCount[leftChar]--;
                
                // If the frequency of the left character drops below the desired frequency in t
                if (tCount.count(leftChar) && windowCount[leftChar] < tCount[leftChar]) {
                    formed--;
                }
                
                // Move the left pointer ahead for the next iteration
                left++;
            }
            
            // Keep expanding the window by moving right pointer
            right++;
        }
        
        // Return the smallest window or empty string if no valid window exists
        return minLen == INT_MAX ? "" : s.substr(minLeft, minLen);
    }
};

/**
 * Main function to test the solution
 */
int main() {
    Solution solution;
    
    // Test case 1
    string s1 = "ADOBECODEBANC";
    string t1 = "ABC";
    cout << "Test 1:" << endl;
    cout << "Input: s = \"" << s1 << "\", t = \"" << t1 << "\"" << endl;
    cout << "Output: \"" << solution.minWindow(s1, t1) << "\"" << endl;
    cout << "Expected: \"ADOBEC\"" << endl << endl;
    
    // Test case 2
    string s2 = "a";
    string t2 = "a";
    cout << "Test 2:" << endl;
    cout << "Input: s = \"" << s2 << "\", t = \"" << t2 << "\"" << endl;
    cout << "Output: \"" << solution.minWindow(s2, t2) << "\"" << endl;
    cout << "Expected: \"a\"" << endl << endl;
    
    // Test case 3
    string s3 = "a";
    string t3 = "aa";
    cout << "Test 3:" << endl;
    cout << "Input: s = \"" << s3 << "\", t = \"" << t3 << "\"" << endl;
    cout << "Output: \"" << solution.minWindow(s3, t3) << "\"" << endl;
    cout << "Expected: \"\"" << endl << endl;
    
    // Test case 4
    string s4 = "ab";
    string t4 = "b";
    cout << "Test 4:" << endl;
    cout << "Input: s = \"" << s4 << "\", t = \"" << t4 << "\"" << endl;
    cout << "Output: \"" << solution.minWindow(s4, t4) << "\"" << endl;
    cout << "Expected: \"b\"" << endl << endl;
    
    // Test case 5
    string s5 = "abc";
    string t5 = "cdc";
    cout << "Test 5:" << endl;
    cout << "Input: s = \"" << s5 << "\", t = \"" << t5 << "\"" << endl;
    cout << "Output: \"" << solution.minWindow(s5, t5) << "\"" << endl;
    cout << "Expected: \"\"" << endl;
    
    return 0;
}
