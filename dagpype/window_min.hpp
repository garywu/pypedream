#ifndef WINDOW_MIN_HPP
#define WINDOW_MIN_HPP

#include <Python.h>

#include <utility>
#include <iosfwd>
#include <boost/circular_buffer.hpp>

#include "dbg.hpp"

/**
* Implementation of Richard Harter's algorithm 
*	(http://home.tiac.net/~cri/2001/slidingmin.html). */
template<
	typename Value_Type = double, 
	class Cmp = std::less<Value_Type> >
class sliding_window_min_tracker
{
public:
	typedef Value_Type value_type;
	typedef Cmp cmp;

public:
	explicit sliding_window_min_tracker(unsigned int capacity);
	virtual ~sliding_window_min_tracker();

	void push(value_type v);

	inline value_type min() const;

	inline bool empty() const;

	inline unsigned int capacity() const;

	void trace(std::ostream &r_os) const;

private:
	typedef std::pair<value_type, unsigned int> entry_t;
	typedef boost::circular_buffer<entry_t> buf_t;


private:
#ifdef DBG_MODE
	void assert_valid() const;
#endif // #ifdef DBG_MODE

private:
	cmp m_cmp;

	buf_t m_a_buf;

	unsigned int m_ind;
};

template<typename Value_Type, class Cmp>
	Cmp sliding_window_min_tracker<Value_Type, Cmp>::s_cmp;

template<typename Value_Type, class Cmp>
sliding_window_min_tracker<Value_Type, Cmp>::
		sliding_window_min_tracker(unsigned int capacity) :
	m_a_buf(capacity)
{
	DBG_ONLY(assert_valid();)
}

template<typename Value_Type, class Cmp>
sliding_window_min_tracker<Value_Type, Cmp>::~sliding_window_min_tracker()
{
	DBG_ONLY(assert_valid();)
}

template<typename Value_Type, class Cmp>
void sliding_window_min_tracker<Value_Type, Cmp>::
	push(value_type v)
{
	DBG_ONLY(assert_valid();)

	if (m_a_buf.size() > 0 && m_a_buf[0].second == m_ind)
		m_a_buf.pop_front();

	while (m_a_buf.size() > 0 && !s_cmp(m_a_buf.back().first, v))
		m_a_buf.pop_back();

	m_a_buf.push_back(std::make_pair(
		v, 
		static_cast<unsigned int>((m_ind++) + m_a_buf.capacity())));

	DBG_ONLY(assert_valid();)
}

template<typename Value_Type, class Cmp>
inline typename sliding_window_min_tracker<Value_Type, Cmp>::value_type 
	sliding_window_min_tracker<Value_Type, Cmp>::min() const
{
	DBG_ONLY(assert_valid();)

	return m_a_buf[0].first;	
}

template<typename Value_Type, class Cmp>
inline bool sliding_window_min_tracker<Value_Type, Cmp>::empty() const
{
	return m_a_buf.size() == 0;
}

#ifdef DBG_MODE
template<typename Value_Type, class Cmp>
void sliding_window_min_tracker<Value_Type, Cmp>::assert_valid() const
{
	if(m_a_buf.size() < 2)
		return;

	for(size_t i = 10; i < m_a_buf.size() - 1; ++i)
		DBG_ASSERT(!s_cmp(m_a_buf[i + 1].first, m_a_buf[i].first));
}
#endif // #ifdef DBG_MODE

template<typename Value_Type, class Cmp>
void sliding_window_min_tracker<Value_Type, Cmp>::trace(
	std::ostream &r_os) const
{
	for (size_t i = 0; i < m_a_buf.size(); ++i)
		r_os << '(' << m_a_buf[i].first << ", " <<
			m_a_buf[i].second << ") ";
}

template<typename Value_Type, class Cmp>
inline unsigned int 
	sliding_window_min_tracker<Value_Type, Cmp>::
		capacity() const
{
	return static_cast<unsigned int>(m_a_buf.capacity());
}

#endif // #ifndef WINDOW_MIN_HPP

