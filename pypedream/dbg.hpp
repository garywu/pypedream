#include <Python.h>

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <sstream>
#include <string>


#undef DBG_MODULE_NAME

/// Set here the name of your module.
#define DBG_MODULE_NAME dagpype

/// Comment/uncomment here to set release/debug modes.
// #define DBG_MODE
#undef DBG_MODE
/// Comment/uncomment here to set extra debug mode.
// #define DBG_EXTRA_MODE


#if defined(DBG_EXTRA_MODE) && !defined(DBG_MODE)
#error Cannot set extra debug mode without debug mode.
#endif // #if defined(DBG_EXTRA_MODE) && !defined(DBG_MODE)


#ifndef DBG_MODULE_NAME_DBG_FNS
#define DBG_MODULE_NAME_DBG_FNS


/******************************************************************************
*******************************************************************************
******************************************************************************/
namespace detail
{


inline void dbg_log(const char file_name[], 
	unsigned int line_num, const std::string &r_msg, std::ostream &r_os)
{
	r_os << file_name << "::" << line_num << ": " << r_msg << "\n";
	// r_os << r_msg << "\n";
}


inline void dbg_warn(const char file_name[], 
	unsigned int line_num, const std::string &r_msg)
{
	dbg_log(file_name, line_num, r_msg, std::cerr);
}


inline void dbg_trace(const char file_name[], 
	unsigned int line_num, const std::string &r_msg)
{
	dbg_log(file_name, line_num, r_msg, std::cout);
}


inline void dbg_assert(const char file_name[], 
	unsigned int line_num, 
	bool cond, const char cond_str[])
{
	if(cond)
		return;

	const std::string assertion = 
		std::string("assertion ") + cond_str + " failed";

	dbg_warn(file_name, line_num, assertion);

	std::abort();
}


template<class Ex_T>
inline void dbg_warn_and_throw(const char file_name[], 
	unsigned int line_num, const std::string &r_msg, 
	const char ex_name[])
{
	const std::string throwing = 
		std::string("throwing ") + ex_name + " - " + r_msg;

	dbg_warn(file_name, line_num, throwing);

	throw Ex_T(r_msg);
}


/******************************************************************************
*******************************************************************************
******************************************************************************/
} // namespace detail


#endif // #ifndef DBG_MODULE_NAME_DBG_FNS


#define DBG_UNCONDITIONAL_ASSERT(COND) ::detail::dbg_assert(\
	__FILE__, __LINE__, (COND), #COND)

#undef DBG_ASSERT
#ifdef DBG_MODE
#define DBG_ASSERT(COND) DBG_UNCONDITIONAL_ASSERT(COND)
#else // #ifdef DBG_MODE
#define DBG_ASSERT(COND)
#endif // #ifdef DBG_MODE

#ifdef DBG_EXTRA_MODE
#define DBG_EXTRA_ASSERT(COND) DBG_UNCONDITIONAL_ASSERT(COND)
#else // #ifdef DBG_EXTRA_MODE
#define DBG_EXTRA_ASSERT(COND)
#endif // #ifdef DBG_EXTRA_MODE

#define DBG_VERIFY(COND) DBG_UNCONDITIONAL_ASSERT(COND)


#undef DBG_ONLY
#ifdef DBG_MODE
#define DBG_ONLY(X) X
#else // #ifdef DBG_MODE
#define DBG_ONLY(X)  
#endif // #ifdef DBG_MODE


#ifdef DBG_EXTRA_MODE
#define DBG_EXTRA_ONLY(X) X
#else // #ifdef DBG_EXTRA_MODE
#define DBG_EXTRA_ONLY(X)  
#endif // #ifdef DBG_EXTRA_MODE


#undef WARN_AND_THROW
#define WARN_AND_THROW(MSG, EX) \
{ \
	std::ostringstream oss; \
	\
	oss << MSG; \
	\
	::detail::dbg_warn_and_throw<EX>( \
		__FILE__, __LINE__, oss.str(), #EX);  \
}


#undef TRACE
#define TRACE(MSG) \
{ \
	std::ostringstream oss; \
	\
	oss << MSG; \
	\
	::detail::dbg_trace( \
		__FILE__, __LINE__, oss.str());  \
}


#undef WARN
#define WARN(MSG) \
{ \
	std::ostringstream oss; \
	\
	oss << MSG; \
	\
	::detail::dbg_warn( \
		__FILE__, __LINE__, oss.str());  \
}

