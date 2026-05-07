package com.dar.server_rmi;

/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */

/**
 *
 * @author José Luis Martín Vera y Pablo Serra García
 */
import java.util.*;

public class Json {

    public static String stringify(Object obj) {
        if (obj == null) return "null";
        if (obj instanceof String) return "\"" + obj + "\"";
        if (obj instanceof Number || obj instanceof Boolean) return obj.toString();
        
        if (obj instanceof List<?>) {
            StringJoiner sj = new StringJoiner(",", "[", "]");
            for (Object item : (List<?>) obj) sj.add(stringify(item));
            return sj.toString();
        }
        
        if (obj instanceof Map<?, ?>) {
            StringJoiner sj = new StringJoiner(",", "{", "}");
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) obj).entrySet()) {
                sj.add("\"" + entry.getKey() + "\":" + stringify(entry.getValue()));
            }
            return sj.toString();
        }
        return "null";
    }

    public static Object parse(String json) {
        return new Object() {
            int pos = 0;
            Object decode() {
                skip();
                char c = json.charAt(pos);
                if (c == '{') return map();
                if (c == '[') return list();
                if (c == '"') return str();
                return num();
            }
            void skip() { while (pos < json.length() && json.charAt(pos) <= ' ') pos++; }
            
            String str() {
                int start = ++pos;
                while (json.charAt(pos) != '"') pos++;
                return json.substring(start, pos++);
            }
            
            Map<String, Object> map() {
                Map<String, Object> m = new LinkedHashMap<>();
                pos++; // skip '{'
                skip();
                while (json.charAt(pos) != '}') {
                    String key = str();
                    skip(); // skip whitespace before ':'
                    pos++; // skip ':'
                    m.put(key, decode());
                    skip(); // skip whitespace before ',' or '}'
                    if (json.charAt(pos) == ',') pos++;
                    skip();
                }
                pos++;
                return m;
            }

            List<Object> list() {
                List<Object> l = new ArrayList<>();
                pos++; // skip '['
                skip();
                while (json.charAt(pos) != ']') {
                    l.add(decode());
                    skip(); // skip whitespace before ',' or ']'
                    if (json.charAt(pos) == ',') pos++;
                    skip();
                }
                pos++;
                return l;
            }

            Object num() {
                int start = pos;
                while (pos < json.length() && "-0123456789.eE+".indexOf(json.charAt(pos)) != -1) pos++;
                String n = json.substring(start, pos);
                return n.contains(".") || n.contains("e") || n.contains("E") ? Double.parseDouble(n) : Long.parseLong(n);
            }
        }.decode();
    }
}
