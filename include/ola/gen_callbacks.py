#!/usr/bin/python
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Library General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# gen_callbacks.py
# Copyright (C) 2010 Simon Newton


import textwrap


def PrintLongLine(line):
  optional_nolint = ''
  if len(line) > 80:
    optional_nolint = '  // NOLINT(whitespace/line_length)'
  print ('%s%s' % (line, optional_nolint))


def Header():
  print textwrap.dedent("""\
  /*
   * This library is free software; you can redistribute it and/or
   * modify it under the terms of the GNU Lesser General Public
   * License as published by the Free Software Foundation; either
   * version 2.1 of the License, or (at your option) any later version.
   *
   * This library is distributed in the hope that it will be useful,
   * but WITHOUT ANY WARRANTY; without even the implied warranty of
   * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   * Lesser General Public License for more details.
   *
   * You should have received a copy of the GNU Lesser General Public
   * License along with this library; if not, write to the Free Software
   * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 \
USA
   *
   * Callback.h
   * @brief Function objects.
   * Copyright (C) 2005 Simon Newton
   *
   * THIS FILE IS AUTOGENERATED!
   * Please edit and run gen_callbacks.py if you need to add more types.
   */

  /**
   * @defgroup callbacks Callbacks
   * @brief Function objects.
   *
   * Callbacks are powerful objects that behave like function pointers. They
   * can be constructed with a pointer to a either plain function or member
   * function. Arguments can be provided at either creation time or execution
   * time.
   *
   * The SingleUse variant of a Callback automatically delete itself after it
   * has been executed.
   *
   * Callbacks are used throughout OLA to reduce the coupling between classes
   * and make for more modular code.
   *
   * Avoid creating Callbacks by directly calling the constructor. Instead use
   * the NewSingleCallback() and NewCallback() helper methods.
   *
   * @examplepara Simple function pointer replacement.
   *   @code
   *   // wrap a function that takes no args and returns a bool
   *   SingleUseCallback<bool> *callback1 = NewSingleCallback(&Function0);
   *
   *   // some time later
   *   bool result = callback1->Run();
   *   // callback1 has deleted itself at this point
   *   @endcode
   *
   * @examplepara Method pointer with a single bound argument
   *   @code
   *   // Create a Callback for Method1 of the Object class and bind TEST_VALUE
   *   // as the first argument.
   *   Callback<void> *callback2 = NewCallback(object, &Object::Method1,
   *                                           TEST_VALUE);
   *
   *   // This will call object->Method1(TEST_VALUE)
   *   callback2->Run();
   *   // this wasn't a SingleUse Callback, so callback is still around and
   *   // needs to be deleted manually.
   *   delete callback2;
   *   @endcode
   *
   * @examplepara Method pointer that takes a single argument at execution time.
   *   @code
   *   // Create a Callback for a method that takes 1 argument and returns void.
   *   BaseCallback1<void, unsigned int> *callback3 = NewCallback(
   *       object, &Object::Method1);
   *
   *   // Call object->Method1(TEST_VALUE)
   *   callback3->Run(TEST_VALUE);
   *   // callback3 is still around at this stage
   *   delete callback3;
   *   @endcode
   *
   * @examplepara Method pointer with one bound argument and one execution time
   * argument.
   *   @code
   *   // Create a callback for a method that takes 2 args and returns void
   *   BaseCallback2<void, int, int> *callback4 = NewSingleCallback(
   *       object,
   *       &Object::Method2,
   *       TEST_VALUE);
   *
   *   // This calls object->Method2(TEST_VALUE, TEST_VALUE2);
   *   callback4->Run(TEST_VALUE2);
   *   // callback4 is still around
   *   delete callback4;
   *   @endcode
   *
   * @note The code in Callback.h is autogenerated by gen_callbacks.py. Please
   * edit and run gen_callbacks.py if you need to add more types.
   *
   */

  /**
   * @addtogroup callbacks
   * @{
   * @file Callback.h
   * @}
   */

  #ifndef INCLUDE_OLA_CALLBACK_H_
  #define INCLUDE_OLA_CALLBACK_H_

  namespace ola {

  /**
   * @addtogroup callbacks
   * @{
   */
  """)


def Footer():
  print textwrap.dedent("""\
  /**
   * @}
   */
  }  // namespace ola
  #endif  // INCLUDE_OLA_CALLBACK_H_""")


def GenerateBase(number_of_args):
  """Generate the base Callback classes."""
  optional_comma = ''

  if number_of_args > 0:
    optional_comma = ', '

  typenames = ', '.join('typename Arg%d' % i for i in xrange(number_of_args))
  arg_list = ', '.join('Arg%d arg%d' % (i, i) for i in xrange(number_of_args))
  args = ', '.join('arg%d' % i for i in xrange(number_of_args))

  arg_types = ', '.join('Arg%d' % i for i in xrange(number_of_args))

  # generate the base callback class
  print textwrap.dedent("""\
  /**
   * @brief The base class for all %d argument callbacks.
   */""" % number_of_args)
  PrintLongLine('template <typename ReturnType%s%s>' %
                (optional_comma, typenames))
  print 'class BaseCallback%d {' % number_of_args
  print ' public:'
  print '  virtual ~BaseCallback%d() {}' % number_of_args
  PrintLongLine('  virtual ReturnType Run(%s) = 0;' % arg_list)
  print '};'
  print ''

  # generate the multi-use version of the callback
  print textwrap.dedent("""\
  /**
   * @brief A %d argument callback which can be called multiple times.
   */""" % number_of_args)
  PrintLongLine('template <typename ReturnType%s%s>' %
                (optional_comma, typenames))
  print ('class Callback%d: public BaseCallback%d<ReturnType%s%s> {' %
         (number_of_args, number_of_args, optional_comma, arg_types))
  print ' public:'
  print '  virtual ~Callback%d() {}' % number_of_args
  PrintLongLine('  ReturnType Run(%s) { return this->DoRun(%s); }' %
                (arg_list, args))
  print ' private:'
  print '  virtual ReturnType DoRun(%s) = 0;' % arg_list
  print '};'
  print ''

  # generate the single-use version of the callback
  print textwrap.dedent("""\
  /**
   * @brief A %d argument callback which deletes itself after it's run.
   */""" % number_of_args)
  PrintLongLine('template <typename ReturnType%s%s>' %
                (optional_comma, typenames))
  PrintLongLine("class SingleUseCallback%d: public BaseCallback%d<"
                "ReturnType%s%s> {" %
                (number_of_args, number_of_args, optional_comma, arg_types))
  print ' public:'
  print '  virtual ~SingleUseCallback%d() {}' % number_of_args
  print '  ReturnType Run(%s) {' % arg_list
  print '    ReturnType ret = this->DoRun(%s);' % args
  print '    delete this;'
  print '    return ret;'
  print '  }'
  print ' private:'
  print '  virtual ReturnType DoRun(%s) = 0;' % arg_list
  print '};'
  print ''

  # the void specialization
  print textwrap.dedent("""\
  /**
   * @brief A %d arg, single use callback that returns void.
   */""" % number_of_args)
  print 'template <%s>' % typenames
  PrintLongLine("class SingleUseCallback%d<void%s%s>: public BaseCallback%d<"
                "void%s%s> {" %
                (number_of_args, optional_comma, arg_types, number_of_args,
                 optional_comma, arg_types))
  print ' public:'
  print '  virtual ~SingleUseCallback%d() {}' % number_of_args
  print '  void Run(%s) {' % arg_list
  print '    this->DoRun(%s);' % args
  print '    delete this;'
  print '  }'
  print ' private:'
  print '  virtual void DoRun(%s) = 0;' % arg_list
  print '};'
  print ''


def GenerateHelperFunction(bind_count,
                           exec_count,
                           function_name,
                           parent_class,
                           is_method=True):
  """Generate the helper functions which create callbacks.

  Args:
    bind_count the number of args supplied at create time.
    exec_count the number of args supplied at exec time.
    function_name what to call the helper function
    parent_class the parent class to use
    is_method True if this is a method callback, False if this is a function
      callback.
    """
  optional_comma = ''
  if bind_count > 0 or exec_count > 0:
    optional_comma = ', '

  typenames = (['typename A%d' % i for i in xrange(bind_count)] +
               ['typename Arg%d' % i for i in xrange(exec_count)])
  bind_types = ['A%d' % i for i in xrange(bind_count)]
  exec_types = ['Arg%d' % i for i in xrange(exec_count)]
  method_types = ', '.join(bind_types + exec_types)
  if exec_count > 0:
    exec_types = [''] + exec_types
  exec_type_str = ', '.join(exec_types)
  optional_class, ptr_name, signature = '', 'callback', '*callback'
  if is_method:
    optional_class, ptr_name, signature = (
        'typename Class, ', 'method', 'Class::*method')

  # The single use helper function
  print textwrap.dedent("""\
  /**
   * @brief A helper function to create a new %s with %d
   * create-time arguments and %d execution time arguments.""" %
                        (parent_class, bind_count, exec_count))
  if is_method:
    print " * @tparam Class the class with the member function."
  print " * @tparam ReturnType the return type of the callback."
  for i in xrange(bind_count):
    print " * @tparam A%d a create-time argument type." % i
  for i in xrange(exec_count):
    print " * @tparam Arg%d an exec-time argument type." % i
  if is_method:
    print " * @param object the object to call the member function on."
    print (" * @param method the member function pointer to use when executing "
           "the callback.")
  else:
    print (" * @param callback the function pointer to use when executing the "
           "callback.")
  for i in xrange(bind_count):
    print " * @param a%d a create-time argument." % i
  if is_method:
    print " * @returns The same return value as the member function."
  else:
    print " * @returns The same return value as the function."
  print " */"
  PrintLongLine('template <%stypename ReturnType%s%s>' %
                (optional_class, optional_comma, ', '.join(typenames)))
  PrintLongLine('inline %s%d<ReturnType%s>* %s(' %
                (parent_class, exec_count, exec_type_str, function_name))
  if is_method:
    print '  Class* object,'
  if bind_count:
    print '  ReturnType (%s)(%s),' % (signature, method_types)
    for i in xrange(bind_count):
      suffix = ','
      if i == bind_count - 1:
        suffix = ') {'
      print '  A%d a%d%s' % (i, i, suffix)
  else:
    print '  ReturnType (%s)(%s)) {' % (signature, method_types)

  padding = ''
  if is_method:
    print '  return new MethodCallback%d_%d<Class,' % (bind_count, exec_count)
  else:
    print '  return new FunctionCallback%d_%d<' % (bind_count, exec_count)
    padding = '  '
  PrintLongLine('                               %s%s%d<ReturnType%s>,' %
                (padding, parent_class, exec_count, exec_type_str))
  if bind_count > 0 or exec_count > 0:
    print '                               %sReturnType,' % padding
  else:
    print '                               %sReturnType>(' % padding
  for i in xrange(bind_count):
    if i == bind_count - 1 and exec_count == 0:
      suffix = '>('
    else:
      suffix = ','
    print '                               %sA%d%s' % (padding, i, suffix)
  for i in xrange(exec_count):
    suffix = ','
    if i == exec_count - 1:
      suffix = '>('
    print '                               %sArg%d%s' % (padding, i, suffix)
  if is_method:
    print '      object,'
  if bind_count:
    print '      %s,' % ptr_name
  else:
    print '      %s);' % ptr_name
  for i in xrange(bind_count):
    suffix = ','
    if i == bind_count - 1:
      suffix = ');'
    print '      a%d%s' % (i, suffix)
  print '}'
  print ''
  print ''


def GenerateMethodCallback(bind_count,
                           exec_count,
                           is_method=True):
  """Generate the specific function callback & helper methods.
    bind_count the number of args supplied at create time.
    exec_count the number of args supplied at exec time.
    is_method True if this is a method callback, False if this is a function
      callback.
  """
  optional_comma = ''
  if bind_count > 0 or exec_count > 0:
    optional_comma = ', '

  typenames = (['typename A%d' % i for i in xrange(bind_count)] +
               ['typename Arg%d' % i for i in xrange(exec_count)])

  bind_types = ['A%d' % i for i in xrange(bind_count)]
  exec_types = ['Arg%d' % i for i in xrange(exec_count)]

  method_types = ', '.join(bind_types + exec_types)
  method_args = (['m_a%d' % i for i in xrange(bind_count)] +
                  ['arg%d' % i for i in xrange(exec_count)])

  exec_args = ', '.join(['Arg%d arg%d' % (i, i) for i in xrange(exec_count)])
  bind_args = ', '.join(['A%d a%d' % (i, i) for i in xrange(bind_count)])

  optional_class, method_or_function, class_name = (
      '', 'Function', 'FunctionCallback')
  class_param, signature = '', '*callback'
  if is_method:
    optional_class, method_or_function, class_name = (
        'typename Class, ', 'Method', 'MethodCallback')
    class_param, signature = 'Class *object, ', 'Class::*Method'

  print ("""\
/**
 * @brief A %s callback with %d create-time args and %d exec time args
 */""" % (method_or_function, bind_count, exec_count))
  PrintLongLine('template <%stypename Parent, typename ReturnType%s%s>' %
                (optional_class, optional_comma, ', '.join(typenames)))

  print 'class %s%d_%d: public Parent {' % (class_name, bind_count, exec_count)
  print ' public:'
  if is_method:
    print '  typedef ReturnType (%s)(%s);' % (signature, method_types)
  else:
    print '  typedef ReturnType (*Function)(%s);' % (method_types)

  if bind_count:
    PrintLongLine('  %s%d_%d(%s%s callback, %s):' %
                  (class_name, bind_count, exec_count, class_param,
                   method_or_function, bind_args))
  else:
    optional_explicit = ''
    if bind_count == 0 and method_or_function == 'Function':
      optional_explicit = 'explicit '
    PrintLongLine('  %s%s%d_%d(%s%s callback):' %
                  (optional_explicit, class_name, bind_count, exec_count,
                   class_param, method_or_function))
  print '    Parent(),'
  if is_method:
    print '    m_object(object),'
  if bind_count:
    print '    m_callback(callback),'
    for i in xrange(bind_count):
      suffix = ','
      if i == bind_count - 1:
        suffix = ' {}'
      print '    m_a%d(a%d)%s' % (i, i, suffix)
  else:
    print '    m_callback(callback) {}'
  print '  ReturnType DoRun(%s) {' % exec_args
  if is_method:
    PrintLongLine('    return (m_object->*m_callback)(%s);' %
                  ', '.join(method_args))
  else:
    print '    return m_callback(%s);' % ', '.join(method_args)
  print '  }'

  print ' private:'
  if is_method:
    print '  Class *m_object;'
  print '  %s m_callback;' % method_or_function
  for i in xrange(bind_count):
    print '  A%d m_a%d;' % (i, i)
  print '};'
  print ''
  print ''

  # generate the helper methods
  GenerateHelperFunction(bind_count,
                         exec_count,
                         'NewSingleCallback',
                         'SingleUseCallback',
                         is_method)
  GenerateHelperFunction(bind_count,
                         exec_count,
                         'NewCallback',
                         'Callback',
                         is_method)


def main():
  Header()

  # exec_time : [bind time args]
  calback_types = {
    0: [0, 1, 2, 3, 4],
    1: [0, 1, 2, 3, 4],
    2: [0, 1, 2, 3, 4],
    3: [0, 1, 2, 3, 4],
    4: [0, 1, 2, 3, 4],
  }

  for exec_time in sorted(calback_types):
    GenerateBase(exec_time)
    for bind_time in calback_types[exec_time]:
      GenerateMethodCallback(bind_time, exec_time, is_method=False)
      GenerateMethodCallback(bind_time, exec_time)
  Footer()


if __name__ == '__main__':
  main()
